import hashlib
import json
from pathlib import Path
import re
import tempfile
import unittest
import xml.etree.ElementTree as ET

from approval_workflow.benchmark import ROOT, aggregate, run
from approval_workflow.scenarios import load_cases


class ReportTests(unittest.TestCase):
    def test_fixture_has_separate_development_and_forty_evaluation_contracts(self):
        cases = load_cases()
        self.assertEqual(len([x for x in cases if x["split"] == "evaluation"]), 40)
        self.assertEqual(len([x for x in cases if x["split"] == "development"]), 8)
        self.assertEqual(len({x["id"] for x in cases}), 48)
        self.assertEqual(len({x["action"] for x in cases}), 48)

    def test_external_output_links_resolve_and_chart_is_valid_xml(self):
        with tempfile.TemporaryDirectory(prefix="approval-report-test-") as directory:
            destination = Path(directory) / "external" / "reports"
            metrics = run(destination)
            records = [json.loads(line) for line in (destination / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 48)
            self.assertEqual(metrics["splits"]["evaluation"]["passed"], 40)
            self.assertTrue(metrics["all_passed"])
            self.assertEqual(metrics["model_calls"], 0)
            report = (destination / "case-study.md").read_text(encoding="utf-8")
            for link in re.findall(r'\]\(([^)]+)\)', report):
                self.assertTrue((destination / link).resolve().is_file(), link)
            self.assertEqual(ET.parse(destination / "contracts.svg").getroot().tag, "{http://www.w3.org/2000/svg}svg")
            self.assertEqual(metrics["fixture_sha256"], hashlib.sha256((ROOT / "data/scenarios.json").read_bytes()).hexdigest())

    def test_empty_denominators_and_empty_suite_are_explicitly_na(self):
        self.assertIsNone(aggregate([])["evaluation"]["pass_rate"])
        with tempfile.TemporaryDirectory(prefix="approval-empty-report-") as directory:
            metrics = run(directory, cases=[])
            self.assertIsNone(metrics["all_passed"])
            report = (Path(directory) / "case-study.md").read_text(encoding="utf-8")
            self.assertIn("N/A (no evaluation cases)", report)
            self.assertNotIn("**0/0", report)


if __name__ == "__main__":
    unittest.main()
