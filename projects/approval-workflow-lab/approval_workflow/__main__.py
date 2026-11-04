import argparse
import json
import tempfile

from .benchmark import run
from .scenarios import Sandbox


def main():
    parser = argparse.ArgumentParser(description="Local approval protocol; no external services or model calls")
    commands = parser.add_subparsers(dest="command", required=True)
    benchmark = commands.add_parser("benchmark", help="execute the fixed contract fixture and generate reports")
    benchmark.add_argument("--output", default="results")
    commands.add_parser("demo", help="request, review, approve, execute, and replay a fictional change")
    args = parser.parse_args()
    if args.command == "benchmark":
        metrics = run(args.output)
        print(json.dumps({"splits": metrics["splits"], "all_passed": metrics["all_passed"]}, indent=2))
        return 0 if metrics["all_passed"] else 1
    with tempfile.TemporaryDirectory(prefix="approval-demo-") as directory:
        sandbox = Sandbox(directory)
        request_id = sandbox.request()
        preview = sandbox.engine.review(sandbox.reviewer, request_id)
        token = sandbox.engine.approve(sandbox.reviewer, request_id, preview["payload_digest"])
        first, replay = sandbox.execute(request_id, token), sandbox.execute(request_id, token)
        # Signed bearer approval tokens are deliberately not printed or persisted.
        print(json.dumps({"fictional": True, "review": preview, "first_execution": first,
                          "retry": replay, "state": sandbox.state()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
