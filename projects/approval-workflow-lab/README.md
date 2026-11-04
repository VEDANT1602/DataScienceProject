# Approval Workflow Lab

**A reviewer approves one transaction. The execution service proves it is still the same transaction.**

I built a small SaaS operations workflow to make that boundary inspectable. It changes fictional account plans and support case statuses, with tenant-scoped tools, a distinct reviewer, a signed approval, optimistic versions, and an atomic execution receipt. Everything runs locally with Python's standard library.

This is an original public implementation by Vedant Thaker. It demonstrates engineering methods relevant to independent AI architecture and startup advisory work. It does not reconstruct a client system or establish past employer results.

## Start with the problem

A useful support assistant needs to read account data, compute a few operational metrics, and propose changes. Giving it a general SQL/Python execution tool or passing around an `approved: true` field makes a demo easy. It also makes the permission hard to explain: approved for which tenant, actor, record, payload, version, and time window?

I narrowed the experiment to that question. The model is deliberately outside the experiment. A deterministic router selects registered tools from typed intents, while the workflow service decides whether a proposed state change may execute. The same checks apply whether the caller is a script, a future model adapter, or an application route.

## The framework I implemented

```text
Trusted application identity boundary
  Principal(tenant, actor, roles)       [no model-supplied identity]
               |
       fixed tool registry
        /       |        \
 read-only SQL  KPI     request change
        |       |        |
 physical tenant DB     pending request + exact review preview
                         |
                  distinct reviewer
                         |
                 HMAC approval claims
                         |
              execute + re-check claims/version
                         |
            BEGIN IMMEDIATE transaction
           mutation + receipt + audit COMMIT
```

- **Narrow changes:** `set_plan` and `set_case_status`, with explicit payload schemas and allowed values.
- **One detached payload:** request and execution boundaries take a canonical JSON snapshot before validation. Digests, retry fingerprints, stored requests and mutations all use that snapshot, including while waiting for a database lock.
- **Transaction-bound review:** the approval includes the requester, reviewer, tenant, operation, payload digest, expected version, expiry, and request ID. A reviewer acknowledges the preview's digest.
- **At most one mutation:** duplicate executions return an idempotent receipt. Concurrent calls serialize around the database transaction. A changed request or stale version fails.
- **Bounded reads:** a read-only SQLite connection, table/function authorizer, instruction budget, SQL/column/expression limits, and output row limit. Tenant data lives in separate database files.
- **Registered computation:** four named KPI queries with explicit denominators. There is no arbitrary Python execution surface.
- **Honest evaluation:** 40 original evaluation contracts and eight separate development examples. Each case checks the return outcome, final mutation count, and execution audit count.

## Run it

Python **3.11 or newer**. No packages, API keys, downloads, cloud accounts, model servers, or paid calls are required.

```powershell
python -m approval_workflow demo
python -m unittest discover -s tests -v
python -m approval_workflow benchmark --output results
```

Run these from this project directory. The demo and suite create temporary fictional tenant databases and remove them afterward. Signing keys are generated in memory; approval tokens are not written to result files. `--output` may point to another directory; report links are computed for that location.

The current suite contains 84 tests, including the 48 fixture cases. Two regression tests hold a real writer lock, mutate the caller's dictionary after preflight, and verify that the original request/approved action survives unchanged. The execution test would otherwise apply an unapproved plan value; the request test would persist a different payload from its retry fingerprint.

## Read the evidence

- [Generated case study and measured results](results/case-study.md)
- [Per-case JSONL, including expected and actual outcomes](results/cases.jsonl)
- [Machine-readable metrics and source/fixture hashes](results/metrics.json)
- [Architecture, trust boundary, and known limits](docs/architecture.md)
- [Customer discovery and staged rollout workshop template](docs/rollout-workshop.md)
- [Original fixture and data card](data/DATA_CARD.md)
- [Reusable workshop configuration template](config/workshop-template.json)

The checked-in result is a local contract run. It is not LLM tool-selection accuracy, real fraud detection, a customer adoption metric, or a general security benchmark. The evaluation cases are visible authored contracts, not a statistically independent test population. No production 93%/97% claim is inferred from them.

## Why this tradeoff

The small operation surface makes permissions reviewable. Separate tenant files simplify the data boundary. HMAC demonstrates integrity without adding a provider dependency. Those choices make this a reproducible engineering lab; they do not replace identity verification, key management, a production datastore, or an independent security review.

My next step would be a customer workshop that lists real workflows, operators, allowed actions, rollback needs, and acceptance criteria. I would run proposed changes in shadow mode before allowing a live state change. The [workshop document](docs/rollout-workshop.md) includes that concrete handoff.

## Sources and license

The implementation is original; the design is informed by [OWASP authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html), [OWASP transaction authorization guidance](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html), and the [Python 3.11 SQLite API](https://docs.python.org/3.11/library/sqlite3.html). No tutorial code or third-party dataset is copied.

Code, synthetic fixtures, and original reports are available under the [MIT license](LICENSE).
