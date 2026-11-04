# Data card: fictional SaaS workflow contracts

## Origin and permitted use

All account records, cases, identities, scenario labels, and expected outcomes were created for this original lab. There is no employer data, personal customer information, third-party dataset, or copied incident log. Code, fixture, and original reports are released under the [MIT license](../LICENSE).

## Shape

Each run seeds two tenant databases. Each nonempty tenant contains 12 accounts and 12 support cases. Both tenants reuse `A01` through `A12` and `C01` through `C12`; names carry a tenant prefix to make leaks observable. Plans are standard/pro, active flags are one, and one in four cases is initially resolved. A separate empty fixture exercises a ratio with no denominator.

The [scenario file](scenarios.json) contains eight development examples and 40 evaluation contracts. Each record defines an ID, split, category, action, expected outcome, and number of allowed committed mutations. Python scenario handlers construct the relevant calls; they never execute code supplied by the fixture. Unknown actions are test failures.

## Evaluation protocol

Each case starts with a new temporary sandbox and an in-memory signing key. The logical clock starts at 1,000 seconds for deterministic expiry tests. That value is a fixture clock, not a timestamp of a real action. Every case checks the outcome code, aggregate committed resource-version increments, and number of execution audit events. Specialized actions also check exact resource values, review state, duplicate receipts, tenant-specific names, or denominator behavior.

Development and evaluation actions are separate, but both are authored, visible, deterministic protocol contracts. The evaluation set is not a hidden benchmark or a random sample of customer requests. Fixing a failing regression does not establish generalization. No language model is invoked, so these cases do not measure natural-language planning or resistance of a model to prompt injection.

## What the records support

The run supports claims about the implemented workflow on these enumerated cases: parameter binding, transaction/payload/actor/tenant binding, expiry, role separation, idempotency, stale-version checks, SQL restrictions, and rollback. It does not measure fraud accuracy, real operator review quality, incident rates, production latency, business savings, or historical client performance.

## Output hygiene and reproducibility

The result JSONL omits approval tokens and random request IDs. It retains expected/actual outcomes, state counts, checks, and small synthetic observations. Metrics include the fixture SHA-256, source hashes, and Python/SQLite versions. There is no wall-clock performance comparison. Run commands appear in the [README](../README.md).
