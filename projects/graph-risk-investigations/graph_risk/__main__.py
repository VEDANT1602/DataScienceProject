"""Run a bounded CPU experiment or regenerate its report."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main():
    for setting in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "LOKY_MAX_CPU_COUNT"):
        os.environ.setdefault(setting, "1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("demo", "report"))
    parser.add_argument("--out", type=Path, default=Path("reports"))
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--bootstrap-draws", type=int, default=250)
    args = parser.parse_args()
    if args.command == "report":
        from .report import from_file
        from_file(args.out)
    else:
        from .experiment import run
        metrics = run(args.out, seed=args.seed, draws=args.bootstrap_draws)
        print(json.dumps({"test": metrics["test"], "uncertainty": metrics["uncertainty"]}, indent=2))


if __name__ == "__main__":
    main()
