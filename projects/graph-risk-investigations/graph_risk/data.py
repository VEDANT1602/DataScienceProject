"""Original fictional event mechanism; entity identifiers are never model inputs."""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import random
from pathlib import Path

DAY = 86400
FIELDS = ("event_id", "timestamp", "customer_id", "device_id", "amount", "country_changed",
          "mobile", "cohort", "mechanism_segment", "label", "label_available_at")


def generate(seed: int = 41, scale: int = 1) -> list[dict]:
    """Generate fixed chronological, entity-disjoint cohorts, without seed selection."""
    if scale < 1:
        raise ValueError("scale must be positive")
    rng = random.Random(seed)
    events = []
    for cohort, start, days, count in (("train", 0, 30, 4500),
                                        ("validation", 35, 10, 1800),
                                        ("test", 50, 20, 2700)):
        for i in range(count * scale):
            second = start * DAY + rng.randrange(days * DAY)
            user = rng.randrange(600)
            ring_member = user < 60
            shifted = second >= 60 * DAY
            if ring_member:
                # Unobserved mechanism: coordinated accounts reuse a small device pool.
                device = f"ring-{user // 12}-{rng.randrange(3 if not shifted else 8)}"
            elif rng.random() < 0.045:
                # Benign shared-access terminals are deliberately a confounder.
                device = f"public-{rng.randrange(4)}"
            else:
                device = f"household-{user // 4}-{rng.randrange(2)}"
            country_changed = int(rng.random() < (0.17 if ring_member else 0.04))
            amount = round(min(1400.0, rng.lognormvariate(3.6 + 0.2 * ring_member, 0.85)), 2)
            mobile = int(rng.random() < 0.68)
            probability = 0.007 + 0.025 * country_changed + 0.018 * (amount > 180)
            probability += (0.30 if not shifted else 0.15) * ring_member
            label = int(rng.random() < probability)
            customer_key = hashlib.sha256(f"{cohort}:customer:{user}".encode()).hexdigest()[:12]
            device_key = hashlib.sha256(f"{cohort}:device:{device}".encode()).hexdigest()[:12]
            events.append({"event_id": f"{cohort}-{i:06d}", "timestamp": second,
                           "customer_id": f"{cohort}-c{customer_key}",
                           "device_id": f"{cohort}-d{device_key}", "amount": amount,
                           "country_changed": country_changed, "mobile": mobile,
                           "cohort": cohort, "mechanism_segment": "shifted" if shifted else "original",
                           "label": label, "label_available_at": second + rng.randint(1, 4) * DAY})
    return sorted(events, key=lambda e: (e["timestamp"], e["event_id"]))


def csv_bytes(events: list[dict]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(events)
    return stream.getvalue().encode("utf-8")


def load(path: Path) -> list[dict]:
    raw = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    for row in rows:
        for key in ("timestamp", "country_changed", "mobile", "label", "label_available_at"):
            row[key] = int(row[key])
        row["amount"] = float(row["amount"])
    return rows


def package(events: list[dict], destination: Path) -> dict:
    destination.mkdir(parents=True, exist_ok=True)
    raw = csv_bytes(events)
    packed = io.BytesIO()
    with gzip.GzipFile(fileobj=packed, mode="wb", filename="", mtime=0) as handle:
        handle.write(raw)
    target = destination / "transactions.csv.gz"
    target.write_bytes(packed.getvalue())
    manifest = {"kind": "original_synthetic_transactions", "rows": len(events),
                "csv_sha256": hashlib.sha256(raw).hexdigest(),
                "gzip_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    (destination / "manifest.json").write_bytes((json.dumps(manifest, indent=2) + "\n").encode())
    return manifest
