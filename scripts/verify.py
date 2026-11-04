"""Run each project's contracts in a separate interpreter and record the outcome."""
from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECTS = ("evidence-gate", "point-in-time-risk", "temporal-recommendations")


def child_environment() -> dict[str, str]:
    environment = os.environ.copy()
    for setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "LOKY_MAX_CPU_COUNT"):
        environment.setdefault(setting, "1")
    return environment


def main() -> int:
    outcomes = []
    for name in PROJECTS:
        command = [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"]
        start = time.perf_counter()
        run = subprocess.run(command, cwd=ROOT / "projects" / name,
                             capture_output=True, text=True, env=child_environment())
        output = run.stdout + run.stderr
        counts = re.findall(r"Ran (\d+) tests? in", output)
        count = int(counts[-1]) if counts else 0
        passed = run.returncode == 0 and count > 0 and "\nOK" in output
        print(f"{name}: {'PASS' if passed else 'FAIL'} ({count} tests)")
        if not passed:
            print(output)
        outcomes.append({"project": name, "command": "python -m unittest discover -s tests -v",
                         "tests": count, "passed": passed,
                         "elapsed_seconds": round(time.perf_counter() - start, 3)})
    versions = {}
    for package in ("numpy", "scikit-learn", "matplotlib", "torch"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = None
    summary = {"python": platform.python_version(), "operating_system": platform.system(),
               "dependencies": versions, "projects": outcomes,
               "total_tests": sum(row["tests"] for row in outcomes),
               "all_passed": all(row["passed"] for row in outcomes)}
    destination = ROOT / "reports" / "verification.json"
    destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Total: {summary['total_tests']} tests; all_passed={summary['all_passed']}")
    return 0 if summary["all_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
