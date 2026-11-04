# Architecture and trust boundaries

## What this application is allowed to do

The fictional product has two tenants, `north` and `south`. Each has 12 accounts and 12 support cases in a different SQLite file. The only changes are account-plan changes and support-case status changes. The fixture's account IDs intentionally overlap across tenants so that isolation cannot depend on globally unique IDs.

The trusted application constructs `Principal(tenant, actor, roles)` after its identity and membership checks. This repository does not implement an identity provider, verify a login token, or prove that a reviewer is a human. The demo supplies two distinct trusted identities to exercise the protocol. A future UI must show the exact preview before collecting approval; merely giving a model the reviewer role would defeat the intended human control.

| Boundary | Trusted input | Untrusted input | Enforcement |
| --- | --- | --- | --- |
| Application identity | Principal and tenant registry | Any tenant/actor/role in a tool body | Body fields never create a principal |
| Tool selection | Exact registered intent names | Free text, instructions, unknown tools | Unknown intent fails closed |
| Read | Tenant file selected by registry | SQL and bound parameter values | Read-only URI, authorizer, budget, output cap |
| Request | Requester principal | Operation, payload, version, retry key | Role check, schema, target existence, version |
| Review | Reviewer principal | Request ID, acknowledged digest | Tenant lookup, distinct actor, exact digest, expiry |
| Execution | Signing key and server clock | Approval token and proposed action | Signature, every claim, persisted approval, current version |

## State machine

```text
pending -> approved -> executed
             |
        expired/stale calls fail; state remains approved

same request retry -> original request (no TTL extension)
same reviewer retry -> same approval (no second approval event)
same execution retry -> original receipt (no second mutation)
```

There is no `execute approved=true` shortcut. An HMAC token alone is also insufficient: execution verifies the stored request is approved by a different actor. All approval claims are compared with the persisted request while holding the write transaction.

## The exact approval contract

Claims are canonical JSON, signed with HMAC-SHA256 and encoded as base64url body/signature. The key must contain at least 32 bytes and is trusted configuration. Each new fixture uses a cryptographically generated in-memory key. Tokens include:

- request ID and tenant;
- requesting actor and reviewing actor;
- operation and SHA-256 of canonical payload;
- expected resource version;
- exclusive expiry time (`now >= expiry` rejects).

The service validates the supplied action against the signature before opening the transaction. Inside `BEGIN IMMEDIATE`, it compares all claims with the stored request and runs a version-conditional update. The resource mutation, request receipt, and execution audit event commit together. Any error, including the test failpoint after the update, rolls all three back. Separate connections per operation allow concurrent callers without sharing a SQLite connection across threads.

Both `request_change` and `execute` first take one detached canonical JSON snapshot of the caller's payload. Validation, payload digests, retry fingerprints, stored request data and mutation parameters use only that snapshot. The caller's mutable dictionary is never reused after the boundary. This matters when `BEGIN IMMEDIATE` waits behind another writer: a changed dictionary must not alter an action whose approval has already been checked. Two actual writer-lock regression tests exercise request persistence and execution separately. Serialization failure rejects the input as `invalid_payload`.

An exact replay within the token's lifetime receives the stored receipt, marked `replayed`. It does not execute the action again. The eight-thread contract requires one new mutation, seven replay receipts, and one execution audit event. After expiry, even receipt replay fails; a real service could add a separately authorized receipt-read API.

## Read-only SQL is a constrained local tool

The SQL tool uses a physically separate tenant file opened with `mode=ro`. It sets `query_only`, then installs an authorizer that allows SELECT, reads of `accounts`/`cases`, and a small function allowlist. Reads of requests, audit, schema tables, attached databases, writes, PRAGMAs, extensions, and recursive CTEs are denied. SQLite's special table-only read for `count(*)` is allowed only for the two business tables.

The tool limits SQL to 4,096 characters, values to 65,536 bytes, columns to 64, expression depth to 50, attached databases to zero, and output to 20 rows by default (configurable from 1 to 100). A progress callback interrupts after approximately 50,000 SQLite VM instructions. That is a work budget, not a wall-clock timeout or process memory limit. The tool uses `execute`, never `executescript`, for untrusted SQL; parameter values remain bound data.

The KPI registry contains `active_accounts`, `open_case_count`, `pro_plan_share`, and `resolved_case_share`. A ratio's numerator and denominator are computed in the same SELECT snapshot. Empty denominators return `value: null` and `status: not_applicable`. Counts of zero remain valid zero counts. No `eval`, `exec`, dynamic import, shell, or provider execution is exposed.

## Audit and failure scope

The local audit stores successful request, approval, and execution transitions. It does not store approval bearer tokens or signing keys. Denied calls are recorded in benchmark observations, not appended to the business audit. A production gateway should send denials and identity events to a separate operational log, with redaction and retention rules.

The audit survives a new process/connection, but a database administrator can modify it. This is not an append-only external audit service. A local filesystem administrator or signing-key holder is outside the threat boundary. The application also lacks revocation, key rotation, reviewer delegation, tenancy provisioning, transport/authentication, rate limiting, and a resource scheduler. Do not expose this lab directly as a public service.

## Primary references

- [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html): informed the default-deny policy, boundary definition, request-by-request permission checks, and negative tests.
- [OWASP Transaction Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Transaction_Authorization_Cheat_Sheet.html): informed transaction-specific approvals, immutable review data, permitted transitions, expiry, and final execution checks.
- [Python 3.11 sqlite3 documentation](https://docs.python.org/3.11/library/sqlite3.html): reference for parameter binding, explicit transactions, authorizers, progress callbacks, limits, and read-only connection URIs. The code uses its public standard-library APIs and copies no documentation examples.
