"""Original, fictional transactions. No customer, employer or financial records."""
from __future__ import annotations

import csv
from dataclasses import asdict
from pathlib import Path
import random
import math

from .store import DAY, DecisionEvent


def generate(n: int = 12_000, seed: int = 19) -> list[dict]:
    """Generate 90 days with device-sharing bursts and a declared day-72 shift.

    Label probabilities deliberately depend on engineered temporal signals. This
    makes the data useful for checking machinery, not estimating field accuracy.
    The seed and mechanism are public; there is no hidden external ground truth.
    """
    rng = random.Random(seed)
    times = sorted(rng.randrange(90*DAY) for _ in range(n))
    rows: list[dict] = []
    device_history: dict[str,list[tuple[int,str]]] = {}
    customer_history: dict[str,list[int]] = {}
    customer_devices: set[tuple[str,str]] = set()
    for i,t in enumerate(times):
        day = t//DAY
        customer = f"customer-{rng.randrange(80):03d}"
        campaign = (t//5400) % 7 == 1
        shared = campaign and rng.random() < .68
        if shared:
            device = f"shared-{(t//5400)%3}"
        elif rng.random() < .07:
            device = f"new-{i}"
        else:
            device = f"device-{customer}"
        amount = round(math.exp(rng.gauss(3.6,.85)),2)
        changed = int(rng.random() < (.38 if shared else .035))
        dh = [(ts,c) for ts,c in device_history.get(device,[]) if ts >= t-3600]
        ch = [ts for ts in customer_history.get(customer,[]) if ts >= t-3600]
        sharing = len({c for ts,c in dh if ts<t})
        is_new = (customer,device) not in customer_devices
        # Shared-device risk weakens after the synthetic shift; country signal
        # strengthens. This is concept drift specified in the generator.
        logit = (-4.3 + .65*(amount>140) + (1.15 if day<72 else 2.0)*changed
                 + .75*is_new + (2.0 if day<72 else .7)*(sharing>=2)
                 + .65*(len(ch)>=2) + .4*(shared and amount<30))
        fraud = int(rng.random() < 1/(1+math.exp(-logit)))
        delay_days = rng.randrange(2,8)
        # This is an outcome-side feature available only after an investigation.
        # It is included in the INVALID diagnostic, never in the safe store.
        dispute_marker = int(rng.random() < (.97 if fraud else .008))
        row = asdict(DecisionEvent(f"txn-{i:06d}",t,customer,device,amount,changed,
                                   "mobile" if rng.random()<.58 else "web"))
        row.update({"fraud":fraud, "label_available_at":t+delay_days*DAY,
                    "future_dispute_marker":dispute_marker,
                    "dispute_marker_available_at":t+delay_days*DAY,
                    "segment":"shifted" if day>=72 else "original"})
        rows.append(row)
        device_history[device] = dh+[(t,customer)]
        customer_history[customer] = ch+[t]
        customer_devices.add((customer,device))
    return rows


def decision_event(row: dict) -> DecisionEvent:
    """An explicit field projection is the boundary between outcomes and serving."""
    return DecisionEvent(**{name:row[name] for name in DecisionEvent.__dataclass_fields__})


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def mature_at(row: dict, cutoff: int) -> bool:
    return row["event_time"] < cutoff and row["label_available_at"] <= cutoff


def split_rows(rows: list[dict]) -> dict[str,list[int]]:
    """Selection train frozen day 45; validation closes day 60, observed at 67.

    Final fitting uses only events before day 60 with labels known by day 67.
    Testing starts day 67 and is assessed at day 100. Days 60-67 are an embargo.
    They may update online history but their outcomes never enter model fitting.
    """
    result = {"selection_train":[],"validation":[],"final_train":[],"test":[]}
    for i,row in enumerate(rows):
        t = row["event_time"]
        if t < 45*DAY and mature_at(row,45*DAY):
            result["selection_train"].append(i)
        if 45*DAY <= t < 60*DAY and mature_at(row,67*DAY):
            result["validation"].append(i)
        if t < 60*DAY and mature_at(row,67*DAY):
            result["final_train"].append(i)
        if 67*DAY <= t < 90*DAY and mature_at(row,100*DAY):
            result["test"].append(i)
    return result
