"""Behavioral contracts, including failures that otherwise inflate offline scores."""
import json
import copy
import gzip
import hashlib
from pathlib import Path
import sqlite3
import tempfile
import unittest
import re

import numpy as np

from risklab.data import decision_event, generate, mature_at, split_rows
from risklab.experiment import STATIC, TEMPORAL, queue_metrics
from risklab.store import DAY, DecisionEvent, DuplicateConflict, TemporalFeatureStore


def event(id="a",t=100,customer="c",device="d",amount=20.0):
    return DecisionEvent(id,t,customer,device,amount,0)


class TemporalContractTests(unittest.TestCase):
    def setUp(self): self.store = TemporalFeatureStore()
    def tearDown(self): self.store.close()

    def test_features_exclude_current_and_future_events(self):
        self.store.ingest(event("before",100,amount=10.0))
        self.store.ingest(event("future",300,amount=1000.0))
        snapshot = self.store.features_before(event("decision",200,amount=90.0))
        self.assertEqual(snapshot["customer_count_24h"],1)
        self.assertEqual(snapshot["customer_mean_amount_24h"],10.0)
        self.assertEqual(snapshot["device_count_1h"],1)

    def test_equal_timestamp_peers_are_excluded(self):
        self.store.ingest(event("same-first",100))
        _,snapshot = self.store.ingest(event("same-second",100))
        self.assertEqual(snapshot["customer_count_1h"],0)
        self.assertEqual(snapshot["new_customer_device"],1)

    def test_window_is_left_inclusive_right_exclusive(self):
        self.store.ingest(event("expired",99))
        self.store.ingest(event("boundary",100))
        self.store.ingest(event("recent",200))
        snapshot = self.store.features_before(event("now",3700))
        self.assertEqual(snapshot["customer_count_1h"],2)

    def test_retry_returns_original_snapshot_and_count_does_not_change(self):
        status,original = self.store.ingest(event())
        self.store.ingest(event("next",101))
        status,retried = self.store.ingest(event())
        self.assertEqual(status,"duplicate")
        self.assertEqual(original,retried)
        self.assertEqual(self.store.checkpoint,{"watermark":101,"accepted_count":2})

    def test_conflicting_reused_id_is_rejected_without_mutation(self):
        self.store.ingest(event())
        with self.assertRaises(DuplicateConflict):
            self.store.ingest(event(amount=99.0))
        self.assertEqual(self.store.checkpoint["accepted_count"],1)
        self.assertEqual(self.store.snapshots()[0][1]["customer_count_1h"],0)

    def test_late_event_is_quarantined_and_never_changes_history(self):
        self.store.ingest(event("first",200))
        status,snapshot = self.store.ingest(event("late",100,amount=10000.0))
        self.assertEqual((status,snapshot),("quarantined",None))
        _,snapshot = self.store.ingest(event("later",300))
        self.assertEqual(snapshot["customer_count_1h"],1)
        self.assertEqual(snapshot["customer_mean_amount_24h"],20.0)
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM quarantine").fetchone()[0],1)
        self.assertEqual(self.store.ingest(event("late",100,amount=10000.0))[0],"quarantined")

    def test_failed_feature_write_rolls_back_event_and_checkpoint(self):
        self.store.db.execute("""CREATE TRIGGER simulate_disk_failure BEFORE INSERT ON feature_rows
                               BEGIN SELECT RAISE(FAIL,'simulated write failure'); END""")
        with self.assertRaises(sqlite3.IntegrityError): self.store.ingest(event())
        self.assertEqual(self.store.checkpoint,{"watermark":-1,"accepted_count":0})
        self.assertEqual(self.store.db.execute("SELECT COUNT(*) FROM events").fetchone()[0],0)
        self.store.db.execute("DROP TRIGGER simulate_disk_failure")
        self.assertEqual(self.store.ingest(event())[0],"accepted")

    def test_invalid_amount_never_enters_ledger(self):
        for amount in (-1.0,0.0,float("nan"),float("inf")):
            with self.assertRaises(ValueError): self.store.ingest(event(amount=amount))
        self.assertEqual(self.store.checkpoint["accepted_count"],0)

    def test_restart_and_retries_match_uninterrupted_replay(self):
        events = [event(str(i),i*100,customer=f"c-{i%3}",device=f"d-{i%2}",amount=float(10+i))
                  for i in range(20)]
        self.store.replay(events)
        expected = self.store.snapshots()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"ledger.sqlite"
            with TemporalFeatureStore(path) as store: store.replay(events[:9])
            with TemporalFeatureStore(path) as store:
                counts = store.replay(events[7:])
                self.assertEqual(counts["duplicate"],2)
                self.assertEqual(store.snapshots(),expected)
                self.assertEqual(store.checkpoint,self.store.checkpoint)

    def test_serving_schema_cannot_expose_outcomes(self):
        rows = generate(30)
        projected = decision_event(rows[0])
        self.assertFalse(hasattr(projected,"fraud"))
        self.assertFalse(hasattr(projected,"future_dispute_marker"))
        _,features = self.store.ingest(projected)
        self.assertEqual(set(features),set(TEMPORAL))
        self.assertFalse(set(features)&{"fraud","label_available_at","future_dispute_marker"})


class EvaluationContractTests(unittest.TestCase):
    def test_packaged_dataset_matches_its_integrity_manifest(self):
        project = Path(__file__).resolve().parents[1]
        manifest = json.loads((project/"data/manifest.json").read_text(encoding="utf-8"))
        payload = (project/"data/transactions.csv.gz").read_bytes()
        raw = gzip.decompress(payload)
        self.assertEqual(hashlib.sha256(payload).hexdigest(),manifest["compressed_sha256"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),manifest["decompressed_sha256"])
        self.assertEqual(len(raw.splitlines())-1,manifest["n_transactions"])

    def test_training_waits_until_label_available(self):
        row = {"event_time":DAY,"label_available_at":4*DAY}
        self.assertFalse(mature_at(row,3*DAY))
        self.assertTrue(mature_at(row,4*DAY))
        self.assertFalse(mature_at({"event_time":4*DAY,"label_available_at":4*DAY},4*DAY))

    def test_split_boundaries_respect_deployment_time(self):
        rows = generate(2000)
        splits = split_rows(rows)
        self.assertTrue(set(splits["selection_train"]).isdisjoint(splits["validation"]))
        self.assertTrue(set(splits["final_train"]).isdisjoint(splits["test"]))
        for i in splits["selection_train"]: self.assertLessEqual(rows[i]["label_available_at"],45*DAY)
        for i in splits["validation"]:
            self.assertGreaterEqual(rows[i]["event_time"],45*DAY)
            self.assertLess(rows[i]["event_time"],60*DAY)
            self.assertLessEqual(rows[i]["label_available_at"],67*DAY)
        for i in splits["test"]: self.assertGreaterEqual(rows[i]["event_time"],67*DAY)

    def test_daily_budget_and_deterministic_ties(self):
        y = np.array([1,0,1,0,0,1,0,1])
        scores = np.array([.9,.9,.1,.2,.8,.7,.5,.4])
        days = np.array([1,1,1,1,2,2,2,2])
        metrics = queue_metrics(y,scores,days,budget=.25)
        self.assertEqual(metrics["n_reviewed"],2)
        self.assertEqual(metrics["true_positive_reviews"],1)
        self.assertEqual(metrics["precision_at_daily_budget"],.5)
        self.assertEqual(metrics["recall_at_daily_budget"],.25)

    def test_small_daily_populations_do_not_exceed_capacity(self):
        metrics = queue_metrics(np.array([1,0]),np.array([.8,.2]),np.array([1,1]),.05)
        self.assertEqual(metrics["n_reviewed"],0)
        self.assertEqual(metrics["recall_at_daily_budget"],0)
        self.assertIsNone(metrics["precision_at_daily_budget"])

    def test_zero_positive_segment_keeps_undefined_denominators_explicit(self):
        metrics = queue_metrics(np.zeros(20,dtype=int),np.linspace(0,1,20),np.ones(20,dtype=int),.05)
        self.assertEqual(metrics["n_reviewed"],1)
        self.assertEqual(metrics["precision_at_daily_budget"],0)
        self.assertIsNone(metrics["average_precision"])
        self.assertIsNone(metrics["recall_at_daily_budget"])

    def test_report_and_charts_render_zero_positive_segment_as_na(self):
        from risklab.report import render
        project = Path(__file__).resolve().parents[1]
        fixture = json.loads((project/"artifacts/metrics.json").read_text(encoding="utf-8"))
        for metrics in fixture["test_segments"]["original"].values():
            metrics.update(n_positive=0,prevalence=0,average_precision=None,
                           true_positive_reviews=0,precision_at_daily_budget=0,
                           recall_at_daily_budget=None)
            metrics["false_positive_reviews"] = metrics["n_reviewed"]
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp)
            self.assertFalse(out.is_relative_to(project))
            render(fixture,out)
            report = (out/"REPORT.md").read_text(encoding="utf-8")
            self.assertIn("| 0 | N/A | N/A | N/A | N/A |",report)
            self.assertIn("An omitted AP bar is not a zero score",report)
            self.assertIn("N/A",(out/"shift-comparison.svg").read_text(encoding="utf-8"))
            dataset_href = re.search(r"\[packaged baseline dataset\]\(([^)]+)\)",report).group(1)
            resolved = (out/dataset_href).resolve()
            self.assertTrue(resolved.is_file())
            self.assertEqual(resolved,project/"data/transactions.csv.gz")

    def test_generator_is_reproducible_and_outcomes_arrive_later(self):
        first,second = generate(100),generate(100)
        self.assertEqual(first,second)
        self.assertNotEqual(first,generate(100,seed=20))
        self.assertTrue(all(r["label_available_at"]>r["event_time"] for r in first))
        self.assertTrue(all(r["dispute_marker_available_at"]>r["event_time"] for r in first))
        self.assertTrue(set(STATIC)<set(TEMPORAL))


if __name__ == "__main__": unittest.main()
