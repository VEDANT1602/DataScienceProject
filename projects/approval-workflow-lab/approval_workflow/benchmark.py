"""Reproducible contract results and reports derived from executed cases."""

from collections import Counter
from pathlib import Path
import hashlib
import html
import json
import os
import platform
import sqlite3

from .scenarios import load_cases, run_case


ROOT = Path(__file__).resolve().parents[1]
PERMITTED_OUTCOMES = {"read", "metric", "routed", "executed", "idempotent", "rolled_back"}


def relative_link(source, report_dir):
    return Path(os.path.relpath(source, report_dir)).as_posix()


def aggregate(results):
    splits = {}
    for split in ("development", "evaluation"):
        rows = [row for row in results if row["split"] == split]
        category = {}
        for name in sorted({row["category"] for row in rows}):
            subset = [row for row in rows if row["category"] == name]
            category[name] = {"passed": sum(row["passed"] for row in subset), "total": len(subset)}
        n = len(rows)
        splits[split] = {
            "passed": sum(row["passed"] for row in rows), "total": n,
            "pass_rate": sum(row["passed"] for row in rows) / n if n else None,
            "expected_rejections": sum(row["expected"] not in PERMITTED_OUTCOMES for row in rows),
            "actual_mutations": sum(row["state"]["mutations"] for row in rows),
            "execution_audit_events": sum(row["state"]["execution_audit_events"] for row in rows),
            "by_category": category,
        }
    return splits


def build_svg(metrics):
    categories = metrics["splits"]["evaluation"]["by_category"]
    width, height, left, top = 720, 105 + len(categories) * 34, 175, 67
    largest = max((item["total"] for item in categories.values()), default=1)
    rows = []
    for index, (name, counts) in enumerate(categories.items()):
        y = top + index * 34
        total_width = 380 * counts["total"] / largest
        pass_width = 380 * counts["passed"] / largest
        rows.extend([
            f'<text x="16" y="{y + 16}" fill="#18324b">{html.escape(name)}</text>',
            f'<rect x="{left}" y="{y}" width="{total_width:.1f}" height="23" fill="#ecd9dc"/>',
            f'<rect x="{left}" y="{y}" width="{pass_width:.1f}" height="23" fill="#17796c"/>',
            f'<text x="{left + total_width + 10:.1f}" y="{y + 16}">{counts["passed"]}/{counts["total"]}</text>',
        ])
    return '\n'.join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Approval Workflow Lab: evaluation contracts passed</title>',
        '<desc id="desc">Counts from executed synthetic contract cases, grouped by category. These are not real-world attack coverage or model accuracy.</desc>',
        f'<rect width="{width}" height="{height}" fill="#f6f8fb"/>',
        '<g font-family="Arial, sans-serif" font-size="14">',
        '<text x="16" y="29" font-size="21" font-weight="bold">Does the execution boundary enforce the contract?</text>',
        '<text x="16" y="49" fill="#46596d">Passed / evaluated cases. Each case uses fresh fictional tenant databases.</text>',
        *rows,
        f'<text x="16" y="{height - 13}" fill="#46596d">Fixed regression suite; no LLM calls, paid services, or production-security claim.</text>',
        '</g>', '</svg>', '',
    ])


def build_report(metrics, results, output):
    ev, dev = metrics["splits"]["evaluation"], metrics["splits"]["development"]
    by_action = {row["action"]: row for row in results}
    replay = by_action.get("threaded_replay", {}).get("details", {})
    source_link = relative_link(ROOT / "data/scenarios.json", output)
    arch_link = relative_link(ROOT / "docs/architecture.md", output)
    card_link = relative_link(ROOT / "data/DATA_CARD.md", output)
    ratio = f'{ev["passed"]}/{ev["total"]}' if ev["total"] else "N/A (no evaluation cases)"
    category_rows = '\n'.join(f'| {name} | {n["passed"]} | {n["total"]} |' for name, n in ev["by_category"].items())
    return f'''# Approval Workflow Lab: the permission belongs to the transaction

The execution boundary passed **{ratio} fixed evaluation contracts**. The separate development suite passed {dev["passed"]}/{dev["total"]}. This is evidence for a small implemented protocol, not a model accuracy score, penetration test, or record of a customer deployment.

## The question I chose

When a support assistant suggests a plan change, what exactly did the reviewer approve? I narrowed that question to two fictional SaaS actions: change an account plan and change a support case status. A useful answer has to survive retries, a different tenant, a changed payload, and a stale record version.

## The usual shortcut and its failure mode

A tool returning `approved: true` does not bind permission to the action that will eventually run. The account, operator, payload, or version can change between review and execution. I implemented the authorization check at the database mutation boundary, where the current record version and the signed approval can be checked together.

## My framework

1. Start with a trusted application principal and a fixed tenant database registry.
2. Register narrow tools and snapshot each change payload before validation. Use that detached value for every digest, retry fingerprint, stored request and mutation; treat instructions and SQL strings as untrusted inputs.
3. Persist a change request and show its exact operation, payload digest, version, and expiry to a different reviewer.
4. Sign that transaction's claims; re-check every binding when execution begins.
5. Commit the mutation, idempotent receipt, and execution audit event in one SQLite transaction.
6. Evaluate state and audit outcomes as well as return codes.

The contract router accepts exact typed intents. It does not interpret natural language and it makes no LLM calls. I used synthetic approval and injection attempts to test the enforcement boundary, without scoring an imaginary agent.

## What the run actually showed

| Evaluation category | Passed | Cases |
| --- | ---: | ---: |
{category_rows}

- Expected rejection cases: {ev["expected_rejections"]}. A pass requires the expected error and the expected database state.
- Committed resource mutations across fresh evaluation sandboxes: {ev["actual_mutations"]}; matching execution audit events: {ev["execution_audit_events"]}.
- Concurrent replay case: {replay.get("calls", "N/A")} calls, {replay.get("new_executions", "N/A")} newly applied mutation, {replay.get("replayed_receipts", "N/A")} cached receipts. Duplicate calls receive the same result; they do not apply another mutation.
- The failure-injection case raised after the SQL update. The resource version stayed at zero, the request stayed approved, and no execution receipt or execution audit event survived.
- Separate writer-lock regression tests mutate caller-owned payload dictionaries after preflight. Both request persistence and execution retain their original snapshots, so a later caller mutation cannot substitute an unapproved action while the transaction waits.
- Ratio KPIs retain their denominator. An empty denominator produces `null` and `not_applicable`, not an invented zero percent.

![Evaluation contract counts](contracts.svg)

## What I would challenge before rollout

Passing these cases does not establish resistance to every SQL or authorization attack. Principals are trusted inputs here; a production service needs verified identity, tenant membership, role provisioning, key storage/rotation, rate limits, independent review, and operational incident logging. The audit database is durable local evidence, not administrator-proof storage. SQL budget units are SQLite virtual-machine instructions, not wall-clock or memory isolation.

The evaluation fixture is a frozen, authored contract set separated from eight development examples. Its expected outcomes are visible in the repository. It is not an independently collected or statistically held-out user distribution. I would next run customer-approved workflow examples in shadow mode, review every proposed change with an operator, and record disagreements before enabling any real mutation.

## Reproduce and inspect

Run `python -m approval_workflow benchmark --output results` from the project folder, then `python -m unittest discover -s tests -v`. The signing key is generated in memory; each case creates and removes fresh local SQLite fixtures.

- [Executed case records](cases.jsonl)
- [Machine-readable metrics](metrics.json)
- [Original scenario fixture]({source_link})
- [Data card]({card_link})
- [Architecture and trust boundaries]({arch_link})

Fixture SHA-256: `{metrics["fixture_sha256"]}`.
'''


def run(output, cases=None):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    cases = load_cases() if cases is None else cases
    results = [run_case(case) for case in cases]
    sources = sorted((ROOT / "approval_workflow").glob("*.py"))
    metrics = {
        "schema_version": 1,
        "measurement": "deterministic synthetic protocol contracts; not LLM accuracy",
        "model_calls": 0, "network_calls": 0, "paid_service_calls": 0,
        "fixture_sha256": hashlib.sha256((ROOT / "data/scenarios.json").read_bytes()).hexdigest(),
        "source_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources},
        "runtime": {"python": platform.python_version(), "sqlite": sqlite3.sqlite_version},
        "splits": aggregate(results),
        "all_passed": all(row["passed"] for row in results) if results else None,
    }
    (output / "cases.jsonl").write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in results), encoding="utf-8", newline="\n")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + '\n', encoding="utf-8", newline="\n")
    (output / "contracts.svg").write_text(build_svg(metrics), encoding="utf-8", newline="\n")
    (output / "case-study.md").write_text(build_report(metrics, results, output), encoding="utf-8", newline="\n")
    return metrics
