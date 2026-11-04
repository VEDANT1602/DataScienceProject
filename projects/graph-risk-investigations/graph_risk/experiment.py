"""Freeze the estimator and temporal contract before evaluating the test cohort."""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import platform
import time

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier

from .data import DAY, csv_bytes, generate, package
from .graph import STATIC, GRAPH, build_features, canonical_events, eligible, ensure_disjoint
from .metrics import calculate, paired_interval, review_indices

PROJECT = Path(__file__).resolve().parents[1]
PARAMETERS = {"max_iter": 100, "max_leaf_nodes": 7, "min_samples_leaf": 20,
              "learning_rate": 0.08, "l2_regularization": 1.0, "random_state": 41}


def matrix(rows, columns):
    return np.asarray([[r["features"][key] for key in columns] for r in rows], dtype=float)


def source_hashes():
    hashes = {p.relative_to(PROJECT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ("graph_risk", "tests") for p in sorted((PROJECT / folder).glob("*.py"))}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    return {"files": hashes, "tree_sha256": digest}


def run(output: Path, seed=41, draws=250):
    start = time.perf_counter()
    events = generate(seed)
    rows = build_features(events)
    ensure_disjoint(rows)
    train = eligible(rows, "train", 35 * DAY)
    validation = eligible(rows, "validation", 50 * DAY)
    test = eligible(rows, "test", 75 * DAY)
    if len({r["label"] for r in train}) < 2:
        raise ValueError("insufficient training outcome classes")
    columns = {"static_hgb": STATIC, "graph_hgb": STATIC + GRAPH}
    validation_metrics = {}
    scores = {}
    final_train = train + validation
    for name, feature_names in columns.items():
        fitted = HistGradientBoostingClassifier(**PARAMETERS)
        fitted.fit(matrix(train, feature_names), [r["label"] for r in train])
        validation_metrics[name] = calculate(validation, fitted.predict_proba(matrix(validation, feature_names))[:, 1])
        fitted.fit(matrix(final_train, feature_names), [r["label"] for r in final_train])
        scores[name] = fitted.predict_proba(matrix(test, feature_names))[:, 1]
    scores["simple_rule"] = matrix(test, STATIC)[:, 0] + 2 * matrix(test, STATIC)[:, 1]
    test_metrics = {name: calculate(test, values) for name, values in scores.items()}
    slices = {segment: {name: calculate([r for r in test if r["mechanism_segment"] == segment],
                                       [s for r, s in zip(test, values) if r["mechanism_segment"] == segment])
                        for name, values in scores.items()}
              for segment in ("original", "shifted")}
    uncertainty = paired_interval(test, scores["static_hgb"], scores["graph_hgb"], draws=draws)
    output.mkdir(parents=True, exist_ok=True)
    data_manifest = package(events, output / "data")
    selected = {name: set(review_indices(test, values)) for name, values in scores.items()}
    predictions = []
    for i, row in enumerate(test):
        predictions.append({"event_id": row["event_id"], "timestamp": row["timestamp"],
                            "segment": row["mechanism_segment"], "label": row["label"],
                            **{name + "_score": float(values[i]) for name, values in scores.items()},
                            **{name + "_reviewed": int(i in indices) for name, indices in selected.items()}})
    with (output / "predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(predictions[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(predictions)
    cards = []
    for i in sorted(selected["graph_hgb"], key=lambda j: (-scores["graph_hgb"][j], test[j]["event_id"]))[:10]:
        row = test[i]
        cards.append({"event_id": row["event_id"], "customer_id": row["customer_id"],
                      "device_id": row["device_id"], "decision_time": row["timestamp"],
                      "ranking_score": float(scores["graph_hgb"][i]),
                      "observations": {k: row["features"][k] for k in GRAPH},
                      "evidence": row["evidence"], "action": "human_review_only",
                      "score_caveat": "Uncalibrated ranking score; not proof of misconduct."})
    (output / "investigation-cards.json").write_bytes((json.dumps(cards, indent=2) + "\n").encode())
    metrics = {"scope": "new independent portfolio reference implementation; synthetic data only",
               "dataset": {**data_manifest, "seed": seed},
               "protocol": {"entity_disjoint_cohorts": True,
                            "event_days": {"train": "[0,30)", "validation": "[35,45)", "test": "[50,70)"},
                            "label_as_of_days": {"train_fit": 35, "validation_and_final_fit": 50, "test_audit": 75},
                            "feature_window": "[t-7days, t); same-timestamp peers excluded",
                            "review_policy": "floor(5% of each day's events), ties by event_id",
                            "hyperparameter_policy": "fixed before experiment; no validation or test search",
                            "feature_identity_fields": [], "parameters_identical_across_hgb_models": PARAMETERS,
                            "graph_features": list(GRAPH), "static_features": list(STATIC)},
               "counts": {"train": len(train), "validation": len(validation), "final_train": len(final_train), "test": len(test)},
               "validation": validation_metrics, "test": test_metrics, "test_slices": slices,
               "uncertainty": uncertainty, "source": source_hashes(),
               "environment": {"python": platform.python_version(), "numpy": np.__version__,
                               "scikit_learn": sklearn.__version__, "os": platform.system(),
                               "cpu_threads_default": 1},
               "runtime_seconds": round(time.perf_counter() - start, 6)}
    (output / "metrics.json").write_bytes((json.dumps(metrics, indent=2) + "\n").encode())
    from .report import render
    render(metrics, output)
    return metrics
