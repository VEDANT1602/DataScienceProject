"""An intentionally small event-time feature store with auditable failure semantics.

Only decision-time fields enter this module. Outcomes live in a separate offline
dataset, so the serving path cannot accidentally read the experiment's labels.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
import sqlite3
from pathlib import Path
from typing import Iterable

DAY = 86_400


@dataclass(frozen=True)
class DecisionEvent:
    event_id: str
    event_time: int
    customer_id: str
    device_id: str
    amount: float
    country_changed: int
    channel: str = "web"

    def validate(self) -> None:
        if not self.event_id or not self.customer_id or not self.device_id:
            raise ValueError("event, customer and device IDs must be nonempty")
        if type(self.event_time) is not int or self.event_time < 0:
            raise ValueError("event_time must be a nonnegative integer in seconds")
        if not math.isfinite(self.amount) or self.amount <= 0:
            raise ValueError("amount must be finite and positive")
        if self.country_changed not in (0, 1):
            raise ValueError("country_changed must be 0 or 1")
        if self.channel not in ("web", "mobile"):
            raise ValueError("channel must be web or mobile")

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


class DuplicateConflict(ValueError):
    """The same event ID was received with different decision-time content."""


class TemporalFeatureStore:
    """SQLite ledger: atomically store an event, its pre-event features and cursor.

    The accepted stream is monotonic in event time. A genuinely older event is
    quarantined rather than retroactively changing decisions. Equal timestamps
    are accepted, but strict ``event_time < decision_time`` excludes all peers at
    that timestamp. This is a conservative tie policy, not Kafka-scale serving.
    """

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.db = sqlite3.connect(str(path))
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS events (
              event_id TEXT PRIMARY KEY, event_time INTEGER NOT NULL,
              customer_id TEXT NOT NULL, device_id TEXT NOT NULL,
              amount REAL NOT NULL, country_changed INTEGER NOT NULL,
              channel TEXT NOT NULL, payload_hash TEXT NOT NULL);
            CREATE INDEX IF NOT EXISTS customer_time ON events(customer_id,event_time);
            CREATE INDEX IF NOT EXISTS device_time ON events(device_id,event_time);
            CREATE TABLE IF NOT EXISTS feature_rows (
              event_id TEXT PRIMARY KEY REFERENCES events(event_id),
              features TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS checkpoint (
              singleton INTEGER PRIMARY KEY CHECK(singleton=1),
              watermark INTEGER NOT NULL, accepted_count INTEGER NOT NULL);
            INSERT OR IGNORE INTO checkpoint VALUES(1,-1,0);
            CREATE TABLE IF NOT EXISTS quarantine (
              event_id TEXT PRIMARY KEY, event_time INTEGER NOT NULL,
              watermark INTEGER NOT NULL, reason TEXT NOT NULL,
              payload_hash TEXT NOT NULL);
        """)

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "TemporalFeatureStore":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @property
    def checkpoint(self) -> dict[str, int]:
        row = self.db.execute("SELECT watermark,accepted_count FROM checkpoint").fetchone()
        return dict(row)

    def features_before(self, event: DecisionEvent) -> dict[str, float]:
        """Calculate history over [t-window,t), never including current/future rows."""
        t = event.event_time
        customer = self.db.execute("""
            SELECT COUNT(*) AS n,COALESCE(AVG(amount),0) AS mean_amount
            FROM events WHERE customer_id=? AND event_time>=? AND event_time<?
        """, (event.customer_id, t-DAY, t)).fetchone()
        customer_hour = self.db.execute("""
            SELECT COUNT(*) FROM events
            WHERE customer_id=? AND event_time>=? AND event_time<?
        """, (event.customer_id, t-3600, t)).fetchone()[0]
        device = self.db.execute("""
            SELECT COUNT(*) AS n,COUNT(DISTINCT customer_id) AS customers
            FROM events WHERE device_id=? AND event_time>=? AND event_time<?
        """, (event.device_id, t-3600, t)).fetchone()
        seen = self.db.execute("""
            SELECT 1 FROM events WHERE customer_id=? AND device_id=? AND event_time<?
            LIMIT 1
        """, (event.customer_id, event.device_id, t)).fetchone() is not None
        mean_amount = float(customer["mean_amount"])
        angle = 2*math.pi*(t % DAY)/DAY
        return {
            "log_amount": math.log1p(event.amount),
            "country_changed": float(event.country_changed),
            "hour_sin": math.sin(angle), "hour_cos": math.cos(angle),
            "mobile": float(event.channel == "mobile"),
            "customer_count_24h": float(customer["n"]),
            "customer_count_1h": float(customer_hour),
            "customer_mean_amount_24h": mean_amount,
            "amount_to_history": min(event.amount/max(mean_amount, 20.0), 100.0),
            "device_count_1h": float(device["n"]),
            "device_customers_1h": float(device["customers"]),
            "new_customer_device": float(not seen),
        }

    def ingest(self, event: DecisionEvent) -> tuple[str, dict[str, float] | None]:
        """Return accepted/duplicate/quarantined and the persisted feature snapshot.

        Concurrent writers are serialized with BEGIN IMMEDIATE. No claim of
        exactly-once delivery is made: duplicate application is prevented by IDs
        plus content hashes, and the side effects are in one SQLite transaction.
        """
        event.validate()
        digest = event.digest()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("""
                SELECT e.payload_hash,f.features FROM events e JOIN feature_rows f
                USING(event_id) WHERE e.event_id=?
            """, (event.event_id,)).fetchone()
            if existing:
                if existing["payload_hash"] != digest:
                    raise DuplicateConflict(event.event_id)
                self.db.commit()
                return "duplicate", json.loads(existing["features"])
            late = self.db.execute("SELECT payload_hash FROM quarantine WHERE event_id=?",
                                   (event.event_id,)).fetchone()
            if late:
                if late["payload_hash"] != digest:
                    raise DuplicateConflict(event.event_id)
                self.db.commit()
                return "quarantined", None
            watermark = self.checkpoint["watermark"]
            if event.event_time < watermark:
                self.db.execute("INSERT INTO quarantine VALUES(?,?,?,?,?)",
                                (event.event_id,event.event_time,watermark,
                                 "older_than_watermark",digest))
                self.db.commit()
                return "quarantined", None
            features = self.features_before(event)
            self.db.execute("INSERT INTO events VALUES(?,?,?,?,?,?,?,?)",
                            (*asdict(event).values(), digest))
            self.db.execute("INSERT INTO feature_rows VALUES(?,?)",
                            (event.event_id,json.dumps(features,sort_keys=True)))
            self.db.execute("""UPDATE checkpoint SET watermark=?,
                            accepted_count=accepted_count+1 WHERE singleton=1""", (event.event_time,))
            self.db.commit()
            return "accepted", features
        except BaseException:
            self.db.rollback()
            raise

    def snapshots(self) -> list[tuple[str, dict[str, float]]]:
        rows = self.db.execute("""SELECT e.event_id,f.features FROM events e
                                JOIN feature_rows f USING(event_id)
                                ORDER BY e.event_time,e.event_id""")
        return [(row[0],json.loads(row[1])) for row in rows]

    def replay(self, events: Iterable[DecisionEvent]) -> dict[str, int]:
        counts = {"accepted":0,"duplicate":0,"quarantined":0}
        for event in events:
            status,_ = self.ingest(event)
            counts[status] += 1
        return counts
