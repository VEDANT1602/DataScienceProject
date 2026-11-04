"""Feature extraction from prior observations, including same-timestamp isolation."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from itertools import groupby
import math

from .data import DAY

STATIC = ("log_amount", "country_changed", "mobile", "hour_sin", "hour_cos")
GRAPH = ("device_users_7d", "customer_devices_7d", "linked_customers_7d",
         "device_events_1h", "customer_events_24h", "new_customer_device",
         "device_events_per_user_7d")


@dataclass(frozen=True)
class Observation:
    timestamp: int
    customer: str
    device: str


class PriorGraph:
    def __init__(self, window: int = 7 * DAY):
        self.window = window
        self.events: deque[Observation] = deque()

    def expire(self, timestamp: int) -> None:
        while self.events and self.events[0].timestamp < timestamp - self.window:
            self.events.popleft()

    def context(self, event: dict) -> tuple[dict, dict]:
        t, customer, device = event["timestamp"], event["customer_id"], event["device_id"]
        prior = [e for e in self.events if t - self.window <= e.timestamp < t]
        devices_by_customer = defaultdict(set)
        users_by_device = defaultdict(set)
        for e in prior:
            devices_by_customer[e.customer].add(e.device)
            users_by_device[e.device].add(e.customer)
        device_users = users_by_device[device]
        customer_devices = devices_by_customer[customer]
        linked = set().union(*(users_by_device[d] for d in customer_devices)) if customer_devices else set()
        linked.discard(customer)
        device_events = [e for e in prior if e.device == device]
        features = {"device_users_7d": len(device_users), "customer_devices_7d": len(customer_devices),
                    "linked_customers_7d": len(linked),
                    "device_events_1h": sum(e.timestamp >= t - 3600 for e in device_events),
                    "customer_events_24h": sum(e.customer == customer and e.timestamp >= t - DAY for e in prior),
                    "new_customer_device": int(device not in customer_devices),
                    "device_events_per_user_7d": len(device_events) / max(1, len(device_users))}
        evidence = {"observed_device_customers": sorted(device_users)[:12],
                    "observed_customer_devices": sorted(customer_devices)[:12],
                    "customer_neighbor_count": len(linked), "window_start": t - self.window,
                    "window_end_exclusive": t,
                    "interpretation": "Observed shared connections are investigation context, not a fraud conclusion."}
        return features, evidence

    def add(self, event: dict) -> None:
        self.events.append(Observation(event["timestamp"], event["customer_id"], event["device_id"]))


def canonical_events(events: list[dict]) -> list[dict]:
    seen = {}
    for event in events:
        if event["amount"] <= 0 or not math.isfinite(event["amount"]):
            raise ValueError("amount must be finite and positive")
        if event["label"] not in (0, 1) or event["label_available_at"] < event["timestamp"]:
            raise ValueError("invalid label or availability timestamp")
        previous = seen.get(event["event_id"])
        if previous is not None and previous != event:
            raise ValueError("conflicting event retry")
        seen[event["event_id"]] = event
    return sorted(seen.values(), key=lambda e: (e["timestamp"], e["event_id"]))


def build_features(events: list[dict]) -> list[dict]:
    graph = PriorGraph()
    result = []
    for timestamp, tied in groupby(canonical_events(events), key=lambda e: e["timestamp"]):
        batch = list(tied)
        graph.expire(timestamp)
        for event in batch:
            values, evidence = graph.context(event)
            angle = (timestamp % DAY) / DAY * 2 * math.pi
            values.update(log_amount=math.log1p(event["amount"]),
                          country_changed=event["country_changed"], mobile=event["mobile"],
                          hour_sin=math.sin(angle), hour_cos=math.cos(angle))
            result.append({**event, "features": values, "evidence": evidence})
        for event in batch:
            graph.add(event)
    return result


def eligible(rows: list[dict], cohort: str, label_as_of: int) -> list[dict]:
    return [r for r in rows if r["cohort"] == cohort and r["label_available_at"] <= label_as_of]


def ensure_disjoint(rows: list[dict]) -> None:
    cohorts = {name: [r for r in rows if r["cohort"] == name]
               for name in ("train", "validation", "test")}
    if any(not values for values in cohorts.values()):
        raise ValueError("all cohorts must be nonempty")
    for left, right in (("train", "validation"), ("validation", "test"), ("train", "test")):
        if max(r["timestamp"] for r in cohorts[left]) >= min(r["timestamp"] for r in cohorts[right]):
            raise ValueError("cohorts overlap in time")
        for field in ("customer_id", "device_id"):
            if {r[field] for r in cohorts[left]} & {r[field] for r in cohorts[right]}:
                raise ValueError("cohorts share entity identifiers")
