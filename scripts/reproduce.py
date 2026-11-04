"""Reproduce demonstrations without overwriting the committed measured artifacts."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-public-data", action="store_true",
                        help="Download MovieLens after reviewing its linked research-use terms")
    args = parser.parse_args()
    runs = ROOT / "runs" / "reproduction"
    jobs = [
        ("evidence-gate", ["-m", "evidence_gate", "benchmark", "--output", str(runs / "evidence-gate")]),
        ("point-in-time-risk", ["-m", "risklab", "demo", "--out", str(runs / "point-in-time-risk")]),
        ("graph-risk-investigations", ["-m", "graph_risk", "demo", "--out", str(runs / "graph-risk-investigations")]),
        ("approval-workflow-lab", ["-m", "approval_workflow", "benchmark", "--output", str(runs / "approval-workflow-lab")]),
        ("inference-systems-lab", ["-m", "inference_lab", "demo", "--out", str(runs / "inference-systems-lab")]),
    ]
    rec_args = ["run.py", "--benchmark", "--output", str(runs / "temporal-recommendations")]
    if args.include_public_data:
        rec_args.append("--download")
    else:
        rec_args.extend(["--data", "data/fixture.tsv"])
    jobs.append(("temporal-recommendations", rec_args))
    for name, arguments in jobs:
        print(f"Running {name}", flush=True)
        environment = os.environ.copy()
        for setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "LOKY_MAX_CPU_COUNT"):
            environment.setdefault(setting, "1")
        subprocess.run([sys.executable, *arguments], cwd=ROOT / "projects" / name,
                       check=True, env=environment)
    print("Fresh outputs: runs/reproduction/. Committed reports were not overwritten.")
    if not args.include_public_data:
        print("Recommendations used the tiny original fixture; see committed reports for the MovieLens experiment.")


if __name__ == "__main__":
    main()
