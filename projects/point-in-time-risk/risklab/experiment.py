"""A reproducible comparison whose test window cannot select its model."""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import time

import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .data import decision_event, generate, split_rows, write_csv
from .store import DAY, DecisionEvent, TemporalFeatureStore

STATIC = ["log_amount","country_changed","hour_sin","hour_cos","mobile"]
TEMPORAL = STATIC + ["customer_count_24h","customer_count_1h",
    "customer_mean_amount_24h","amount_to_history","device_count_1h",
    "device_customers_1h","new_customer_device"]


def queue_metrics(y: np.ndarray, scores: np.ndarray, days: np.ndarray,
                  budget: float = .05) -> dict:
    """Rank a daily review queue, allocating floor(budget * day transactions).

    This is a retrospective capacity-ranking metric, not a calibrated online
    threshold. Ties keep event input order, and the same queue size is applied
    to every model on every day.
    """
    if not 0 <= budget <= 1:
        raise ValueError("budget must be between zero and one")
    if not (len(y) == len(scores) == len(days)) or not len(y):
        raise ValueError("metrics require nonempty aligned arrays")
    selected = []
    for day in sorted(set(days.tolist())):
        indices = np.flatnonzero(days == day)
        k = math.floor(len(indices)*budget)
        ranked = indices[np.argsort(-scores[indices],kind="stable")]
        selected.extend(ranked[:k].tolist())
    tp = int(y[selected].sum()) if selected else 0
    positives = int(y.sum())
    return {
        "n_transactions":int(len(y)),"n_positive":positives,
        "prevalence":float(y.mean()),
        "average_precision":float(average_precision_score(y,scores)) if positives else None,
        "nominal_daily_review_fraction":budget,
        "n_reviewed":len(selected),"true_positive_reviews":tp,
        "false_positive_reviews":len(selected)-tp,
        "actual_review_fraction":len(selected)/len(y),
        "precision_at_daily_budget":tp/len(selected) if selected else None,
        "recall_at_daily_budget":tp/positives if positives else None,
    }


def day_bootstrap(y: np.ndarray, baseline: np.ndarray, candidate: np.ndarray,
                  days: np.ndarray, draws: int = 200, seed: int = 71) -> dict:
    """Conditional interval for paired AP differences by resampling whole days.

    Fixed fitted models, one simulated stream, no model-retraining uncertainty.
    Shared devices can span days, so this is descriptive rather than a guarantee.
    """
    rng = np.random.default_rng(seed)
    unique = np.unique(days)
    by_day = {d:np.flatnonzero(days == d) for d in unique}
    differences = []
    for _ in range(draws):
        sampled = rng.choice(unique,size=len(unique),replace=True)
        indices = np.concatenate([by_day[d] for d in sampled])
        if y[indices].sum():
            differences.append(average_precision_score(y[indices],candidate[indices])-
                               average_precision_score(y[indices],baseline[indices]))
    low,high = np.quantile(differences,[.025,.975])
    return {"method":"paired day-block percentile bootstrap of fixed predictions",
            "draws":draws,"seed":seed,"ap_difference_low":float(low),
            "ap_difference_high":float(high),"resampled_blocks":len(unique),
            "scope":"descriptive uncertainty within one synthetic stream; not field accuracy"}


def _matrix(features: list[dict], names: list[str]) -> np.ndarray:
    return np.asarray([[f[name] for name in names] for f in features],dtype=np.float64)


def _write_predictions(path: Path, rows: list[dict], indices: list[int], scores: dict) -> None:
    with path.open("w",newline="",encoding="utf-8") as handle:
        writer = csv.writer(handle,lineterminator="\n")
        writer.writerow(["event_id","day","segment","label"]+list(scores))
        for j,i in enumerate(indices):
            row = rows[i]
            writer.writerow([row["event_id"],row["event_time"]//DAY,row["segment"],row["fraud"]]+
                            [format(values[j],".12g") for values in scores.values()])


def run(out: Path, n: int = 12_000, seed: int = 19, bootstrap_draws: int = 200) -> dict:
    if n < 2_000:
        raise ValueError("use at least 2,000 events for the three-window experiment")
    if bootstrap_draws < 20:
        raise ValueError("use at least 20 bootstrap draws")
    out.mkdir(parents=True,exist_ok=True)
    rows = generate(n,seed)
    write_csv(rows,out/"transactions.csv")
    dataset_sha = hashlib.sha256((out/"transactions.csv").read_bytes()).hexdigest()
    # A fresh ledger is required for a repeatable benchmark; never erase a user's
    # arbitrary database. Every run uses a unique local temp SQLite database.
    import tempfile
    with tempfile.TemporaryDirectory(prefix="risklab-") as temp:
        start = time.perf_counter()
        with TemporalFeatureStore(Path(temp)/"replay.sqlite") as store:
            features = []
            replay = {"accepted":0,"duplicate":0,"quarantined":0}
            for i,row in enumerate(rows):
                status,snapshot = store.ingest(decision_event(row))
                replay[status] += 1
                features.append(snapshot)
                if i % 500 == 0:
                    status,_ = store.ingest(decision_event(row))
                    replay[status] += 1
            last = rows[-1]
            # Deliberately older, new IDs demonstrate late policy, not model data.
            for j in range(3):
                late = DecisionEvent(f"late-example-{j}",last["event_time"]-DAY,
                                     "late-customer","late-device",20.0,0)
                status,_ = store.ingest(late)
                replay[status] += 1
            checkpoint = store.checkpoint
            import sqlite3
            destination = sqlite3.connect(out/"replay.sqlite")
            try:
                store.db.backup(destination)
            finally:
                destination.close()
        replay_seconds = time.perf_counter()-start
    splits = split_rows(rows)
    y = np.asarray([row["fraud"] for row in rows])
    days = np.asarray([row["event_time"]//DAY for row in rows])
    X_static,X_temporal = _matrix(features,STATIC),_matrix(features,TEMPORAL)
    train,val,final,test = (splits[name] for name in
                             ("selection_train","validation","final_train","test"))
    if any(len(set(y[idx])) < 2 for idx in (train,val,test)):
        raise ValueError("each evaluation split needs both classes; use more events")
    baseline = make_pipeline(StandardScaler(),LogisticRegression(C=1,max_iter=500,random_state=seed))
    baseline.fit(X_static[train],y[train])
    validation_baseline = queue_metrics(y[val],baseline.predict_proba(X_static[val])[:,1],days[val])
    trials = []
    for leaves in (7,15):
        model = HistGradientBoostingClassifier(max_leaf_nodes=leaves,max_iter=120,
                   learning_rate=.06,l2_regularization=3.0,random_state=seed)
        model.fit(X_temporal[train],y[train])
        metrics = queue_metrics(y[val],model.predict_proba(X_temporal[val])[:,1],days[val])
        trials.append({"max_leaf_nodes":leaves,"metrics":metrics})
    # Only validation AP selects the candidate; fewer leaves breaks exact ties.
    selected = max(trials,key=lambda t:(t["metrics"]["average_precision"],-t["max_leaf_nodes"]))
    candidate = HistGradientBoostingClassifier(max_leaf_nodes=selected["max_leaf_nodes"],max_iter=120,
                   learning_rate=.06,l2_regularization=3.0,random_state=seed)
    baseline.fit(X_static[final],y[final])
    candidate.fit(X_temporal[final],y[final])
    scores = {"static_logistic":baseline.predict_proba(X_static[test])[:,1],
              "temporal_boosting":candidate.predict_proba(X_temporal[test])[:,1]}
    # An exploratory feature ablation holds the fitted algorithm configuration
    # constant. Its result cannot alter the frozen candidate or hyperparameters.
    static_boosting = HistGradientBoostingClassifier(
        max_leaf_nodes=selected["max_leaf_nodes"],max_iter=120,learning_rate=.06,
        l2_regularization=3.0,random_state=seed)
    static_boosting.fit(X_static[final],y[final])
    scores["static_boosting_ablation"] = static_boosting.predict_proba(X_static[test])[:,1]
    # Impossible-at-decision-time information, intentionally isolated. This is
    # never part of selection or a production candidate, even if its score wins.
    X_invalid = np.column_stack((X_temporal,[r["future_dispute_marker"] for r in rows]))
    invalid = HistGradientBoostingClassifier(max_leaf_nodes=7,max_iter=120,
                    learning_rate=.06,l2_regularization=3.0,random_state=seed)
    invalid.fit(X_invalid[final],y[final])
    scores["INVALID_future_marker"] = invalid.predict_proba(X_invalid[test])[:,1]
    metrics = {name:queue_metrics(y[test],score,days[test]) for name,score in scores.items()}
    segments = {}
    for segment in ("original","shifted"):
        mask = np.asarray([rows[i]["segment"]==segment for i in test])
        segments[segment] = {name:queue_metrics(y[test][mask],score[mask],days[test][mask])
                             for name,score in scores.items()}
    ci = day_bootstrap(y[test],scores["static_logistic"],scores["temporal_boosting"],days[test],
                       draws=bootstrap_draws)
    metrics_contract = {
        "selection_objective":"validation average precision; no holdout tuning",
        "review_policy":"daily offline ranking, floor(0.05 * transactions_per_day)",
        "ties":"original event order (stable descending score sort)",
        "average_precision":"sklearn average_precision_score: non-interpolated precision-recall summary",
        "precision_denominator":"reviewed transactions",
        "recall_denominator":"positive outcome labels in evaluated transactions",
        "units":"fractions unless explicitly named count or seconds",
    }
    result = {
        "project":"Point-in-time Risk", "scope":"new independent portfolio reference implementation",
        "data_kind":"original synthetic transactions; no employer or client data",
        "generator":{"seed":seed,"n_events":n,"n_days":90,"shift_day":72},
        "dataset_sha256":dataset_sha,
        "time_contract":{"selection_train_cutoff_day":45,"validation_event_days":"45 <= day < 60",
                         "validation_label_as_of_day":67,"final_train_event_days":"day < 60",
                         "deployment_freeze_day":67,"test_event_days":"67 <= day < 90",
                         "test_label_as_of_day":100,"maximum_label_delay_days":7},
        "split_counts":{name:len(indices) for name,indices in splits.items()},
        "split_positive_counts":{name:int(y[indices].sum()) for name,indices in splits.items()},
        "training_rows_excluded_for_immature_labels":sum(r["event_time"]<45*DAY for r in rows)-len(train),
        "features":{"baseline":STATIC,"candidate":TEMPORAL,"static_boosting_ablation":STATIC,
                    "invalid_diagnostic_only":"future_dispute_marker"},
        "validation":{"baseline":validation_baseline,"candidate_trials":trials,
                      "selected_max_leaf_nodes":selected["max_leaf_nodes"]},
        "test":metrics,"test_segments":segments,"bootstrap":ci,
        "metric_contract":metrics_contract,
        "ledger":{"replay":replay,"checkpoint":checkpoint,
                  "late_policy":"quarantine older-than-watermark arrivals; do not revise historical decisions",
                  "replay_wall_seconds":round(replay_seconds,6),
                  "accepted_events_per_second_local":round(n/replay_seconds,2)},
        "environment":{"python":platform.python_version(),"os":platform.system(),
                       "numpy":np.__version__,"scikit_learn":sklearn.__version__},
    }
    (out/"metrics.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    _write_predictions(out/"test_predictions.csv",rows,test,scores)
    write_csv(rows[:100],out/"transaction_fixture.csv")
    return result
