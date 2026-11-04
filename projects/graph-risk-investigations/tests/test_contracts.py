from copy import deepcopy
from pathlib import Path
import csv
import gzip
import hashlib
import json
import math
import os
import re
import tempfile
import unittest

for setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "LOKY_MAX_CPU_COUNT"):
    os.environ.setdefault(setting, "1")

import numpy as np

from graph_risk.data import DAY, csv_bytes, generate, package, load
from graph_risk.graph import STATIC, GRAPH, build_features, canonical_events, eligible, ensure_disjoint
from graph_risk.metrics import calculate, paired_interval, review_indices
from graph_risk.report import render


def event(identifier, timestamp, customer="c1", device="d1", label=0, cohort="train"):
    return {"event_id": identifier, "timestamp": timestamp, "customer_id": customer,
            "device_id": device, "amount": 30.0, "country_changed": 0, "mobile": 1,
            "cohort": cohort, "mechanism_segment": "original", "label": label,
            "label_available_at": timestamp + DAY}


class GraphContracts(unittest.TestCase):
    def test_future_events_cannot_change_prior_features(self):
        past = [event("a", 1), event("b", 2, "c2")]
        before = build_features(past)
        after = build_features(past + [event("c", 500, "c3", "d1", 1)])
        self.assertEqual(before, after[:2])

    def test_same_timestamp_edges_are_not_visible_to_each_other(self):
        rows = build_features([event("b", 4, "c2"), event("a", 4)])
        self.assertEqual([r["features"]["device_users_7d"] for r in rows], [0, 0])
        self.assertEqual(rows, build_features([event("a", 4), event("b", 4, "c2")]))

    def test_old_edges_expire_and_boundary_is_inclusive(self):
        rows = build_features([event("a", 1), event("b", 7 * DAY + 1, "c2"),
                               event("c", 7 * DAY + 2, "c3")])
        self.assertEqual(rows[1]["features"]["device_users_7d"], 1)
        self.assertEqual(rows[2]["features"]["device_users_7d"], 1)

    def test_current_connection_is_added_only_after_scoring(self):
        rows = build_features([event("a", 1), event("b", 2)])
        self.assertEqual(rows[0]["features"]["new_customer_device"], 1)
        self.assertEqual(rows[1]["features"]["new_customer_device"], 0)

    def test_exact_retry_is_idempotent(self):
        rows = [event("a", 1), event("a", 1), event("b", 2, "c2")]
        self.assertEqual(len(canonical_events(rows)), 2)
        self.assertEqual(build_features(rows)[1]["features"]["device_events_per_user_7d"], 1)

    def test_conflicting_retry_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "conflicting"):
            canonical_events([event("a", 1), event("a", 1, "c2")])

    def test_labels_and_outcome_delays_are_not_graph_inputs(self):
        rows = [event("a", 1), event("b", 2, "c2")]
        changed = deepcopy(rows)
        for row in changed:
            row["label"] = 1
            row["label_available_at"] += DAY * 50
        before, after = build_features(rows), build_features(changed)
        self.assertEqual([r["features"] for r in before], [r["features"] for r in after])
        self.assertEqual([r["evidence"] for r in before], [r["evidence"] for r in after])

    def test_generator_is_deterministic_and_cohorts_disjoint(self):
        one, two = generate(), generate()
        self.assertEqual(csv_bytes(one), csv_bytes(two))
        ensure_disjoint(one)
        self.assertEqual(len(one), 9000)

    def test_exported_identity_does_not_announce_latent_mechanism(self):
        for row in generate()[:100]:
            self.assertRegex(row["customer_id"], r"^(train|validation|test)-c[0-9a-f]{12}$")
            self.assertRegex(row["device_id"], r"^(train|validation|test)-d[0-9a-f]{12}$")
            self.assertFalse(any(word in row["device_id"] for word in ("ring", "public", "household")))

    def test_shared_test_entity_is_rejected(self):
        rows = [event("a", 1, "a", "a", cohort="train"),
                event("b", 3, "b", "b", cohort="validation"),
                event("c", 5, "a", "c", cohort="test")]
        with self.assertRaisesRegex(ValueError, "share entity"):
            ensure_disjoint(rows)

    def test_label_maturity_filters_the_training_population(self):
        rows = [event("a", 1), event("b", 2)]
        self.assertEqual([r["event_id"] for r in eligible(rows, "train", DAY + 1)], ["a"])

    def test_no_identity_or_outcome_columns_in_matrix_contract(self):
        self.assertFalse({"label", "event_id", "customer_id", "device_id", "cohort", "mechanism_segment"} & set(STATIC + GRAPH))
        self.assertEqual(set(build_features([event("a", 1)])[0]["features"]), set(STATIC + GRAPH))

    def test_capacity_uses_daily_floor_and_stable_event_id_ties(self):
        rows = [event(f"e{i:02d}", i + 1, label=int(i < 3)) for i in range(40)]
        indices = review_indices(rows[::-1], [1.0] * 40)
        self.assertEqual([rows[::-1][i]["event_id"] for i in indices], ["e00", "e01"])
        result = calculate(rows, [1.0] * 40)
        self.assertEqual(result["positive_reviews"], 2)
        self.assertAlmostEqual(result["recall_at_capacity"], 2 / 3)

    def test_negative_day_does_not_borrow_another_days_capacity(self):
        rows = [event(f"a{i}", i + 1) for i in range(19)] + [event(f"b{i}", DAY + i, label=1) for i in range(21)]
        self.assertEqual(len(review_indices(rows, list(range(40)))), 1)

    def test_undefined_metrics_stay_none(self):
        rows = [event("a", 1)]
        result = calculate(rows, [0.4])
        self.assertIsNone(result["average_precision"])
        self.assertIsNone(result["precision_at_capacity"])
        self.assertIsNone(result["recall_at_capacity"])

    def test_metric_math_and_nonfinite_scores(self):
        rows = [event(str(i), i, label=v) for i, v in enumerate([1, 0, 1, 0])]
        self.assertAlmostEqual(calculate(rows, [0.9, 0.8, 0.7, 0.6])["average_precision"], (1 + 2 / 3) / 2)
        with self.assertRaisesRegex(ValueError, "finite"):
            calculate(rows, [1, float("nan"), 2, 3])

    def test_bootstrap_resamples_paired_predictions(self):
        rows = [event(str(i), (i // 10) * DAY + i, label=int(i % 4 == 0)) for i in range(40)]
        scores = np.arange(40) / 40
        interval = paired_interval(rows, scores, scores, draws=20)
        self.assertEqual(interval["ap_difference_lower_95"], 0)
        self.assertEqual(interval["ap_difference_upper_95"], 0)

    def test_packaged_data_is_deterministic_and_round_trips(self):
        rows = [event("a", 1), event("b", 2, "c2")]
        with tempfile.TemporaryDirectory() as tmp:
            one = package(rows, Path(tmp) / "one")
            two = package(rows, Path(tmp) / "two")
            self.assertEqual(one, two)
            self.assertEqual(load(Path(tmp) / "one/transactions.csv.gz"), rows)
            raw = gzip.decompress((Path(tmp) / "one/transactions.csv.gz").read_bytes())
            self.assertEqual(hashlib.sha256(raw).hexdigest(), one["csv_sha256"])

    def test_report_link_resolves_outside_project_and_null_ap_renders(self):
        measure = {"transactions": 20, "positive_outcomes": 0, "average_precision": None,
                   "reviewed": 1, "positive_reviews": 0, "precision_at_capacity": 0.0, "recall_at_capacity": None}
        metrics = {"dataset": {"rows": 100}, "test": {"simple_rule": measure, "static_hgb": measure, "graph_hgb": measure},
                   "test_slices": {"original": {"static_hgb": measure, "graph_hgb": measure}},
                   "uncertainty": {"ap_difference_lower_95": None, "ap_difference_upper_95": None}}
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "outside"
            render(metrics, output)
            text = (output / "case-study.md").read_text()
            self.assertIn("N/A", text)
            link = re.search(r"\[project data card\]\(([^)]+)\)", text).group(1)
            self.assertEqual((output / link).resolve(), (Path(__file__).resolve().parents[1] / "DATA_CARD.md").resolve())
            self.assertTrue((output / link).exists())


if __name__ == "__main__":
    unittest.main()
