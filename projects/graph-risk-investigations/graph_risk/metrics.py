"""Daily queue accounting with fixed capacity and explicit undefined values."""
from __future__ import annotations

import math
import numpy as np
from sklearn.metrics import average_precision_score

from .data import DAY


def review_indices(rows, scores, fraction=0.05):
    if not 0 <= fraction <= 1 or len(rows) != len(scores):
        raise ValueError("invalid capacity or score count")
    if not np.all(np.isfinite(scores)):
        raise ValueError("scores must be finite")
    selected = []
    for day in sorted({r["timestamp"] // DAY for r in rows}):
        indices = [i for i, r in enumerate(rows) if r["timestamp"] // DAY == day]
        indices.sort(key=lambda i: (-scores[i], rows[i]["event_id"]))
        selected.extend(indices[:math.floor(fraction * len(indices))])
    return selected


def calculate(rows, scores, fraction=0.05):
    labels = np.asarray([r["label"] for r in rows])
    selected = review_indices(rows, scores, fraction)
    positives = int(labels.sum())
    found = int(labels[selected].sum()) if selected else 0
    return {"transactions": len(rows), "positive_outcomes": positives,
            "average_precision": float(average_precision_score(labels, scores)) if positives else None,
            "reviewed": len(selected), "positive_reviews": found,
            "precision_at_capacity": found / len(selected) if selected else None,
            "recall_at_capacity": found / positives if positives else None,
            "review_fraction": len(selected) / len(rows) if rows else 0.0}


def paired_interval(rows, baseline, graph, draws=250, seed=2026):
    """Descriptive day-block bootstrap of fixed predictions, not repeated training."""
    if draws < 1:
        raise ValueError("draws must be positive")
    days = sorted({r["timestamp"] // DAY for r in rows})
    by_day = {d: [i for i, r in enumerate(rows) if r["timestamp"] // DAY == d] for d in days}
    rng = np.random.default_rng(seed)
    labels = np.asarray([r["label"] for r in rows])
    values = []
    for _ in range(draws):
        indices = np.concatenate([by_day[d] for d in rng.choice(days, len(days), replace=True)])
        if labels[indices].sum():
            values.append(average_precision_score(labels[indices], np.asarray(graph)[indices]) -
                          average_precision_score(labels[indices], np.asarray(baseline)[indices]))
    interval = np.quantile(values, [0.025, 0.975]) if values else (None, None)
    return {"method": "paired day-block percentile bootstrap of fixed predictions", "draws": draws,
            "seed": seed, "days": len(days), "valid_draws": len(values),
            "ap_difference_lower_95": None if interval[0] is None else float(interval[0]),
            "ap_difference_upper_95": None if interval[1] is None else float(interval[1]),
            "scope": "descriptive uncertainty for one synthetic stream; no population or training-variance claim"}
