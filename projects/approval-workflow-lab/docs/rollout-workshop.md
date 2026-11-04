# A workshop that ends with an executable contract

This is a reusable workshop plan, not a claim that a customer workshop occurred. Use the [configuration template](../config/workshop-template.json) to capture decisions; replace fictional examples only with authorized data.

## 1. Map the workflow before selecting a model

Ask an operator to walk through one account-plan change and one case-status change. Capture the trigger, tenant, current version, requester, reviewer, state mutation, customer consequence, reversibility, and source of truth. Separate an answer that can be read from an action that needs permission.

The output is a table with one row per operation:

| Operation | Requester | Reviewer | Exact review data | Execution precondition | Recovery |
| --- | --- | --- | --- | --- | --- |
| Fictional plan change | Support operator | Different authorized lead | Account ID, old/new plan, version, expiry | Signed request and unchanged version | New reviewed compensating request |
| Fictional case update | Support operator | Different authorized lead | Case ID, old/new status, version, expiry | Signed request and unchanged version | New reviewed compensating request |

Do not infer an actor's role from a prompt, email signature, or model output. The identity owner must describe the actual authentication and membership check.

## 2. Freeze the evaluation contract

Collect approved examples of normal reads, proposed changes, retries, stale records, accidental wrong-tenant requests, malicious instructions, and unauthorized operators. Assign expected tool, expected authorization outcome, and expected final state before running the candidate adapter. Keep development examples separate from the evaluation file. Version the fixture and record its hash.

Score three different questions separately: did the adapter select the appropriate tool; did enforcement accept or reject correctly; and did the database end in the correct state? This lab implements the last two and a typed routing contract. A future LLM adapter needs its own frozen prompts and independently measured tool-selection results.

## 3. Review the architecture with the people who own it

Identify the owner of identity, tenant membership, signing keys, approval UI, customer data access, audit retention, cancellation, and incident response. Verify what happens when a reviewer leaves, a key rotates, a token expires, or the source system changes after approval. Demonstrate an injected transaction failure and a duplicate execution before discussing rollout.

Record unowned decisions as blockers. A working demo is not evidence that operational ownership exists.

## 4. Roll out in stages

| Stage | Allowed behavior | Evidence required to advance |
| --- | --- | --- |
| Local fixture | Synthetic reads and changes | Reproducible contracts, no state/audit mismatch |
| Shadow | Propose changes; no live mutation | Operator review of disagreements on approved examples |
| Reviewed pilot | Small approved operation set | Verified identity, tenant isolation, observable review/receipt path, recovery rehearsal |
| Limited production | Explicitly agreed scope | Named owners, monitored errors/denials, key/revocation plan, agreed rollback trigger |

Measure execution disagreements and tool-selection errors with denominators. Do not quote a pass percentage without naming the fixture, sample count, model/configuration if used, and collection period. The stop conditions are concrete: any cross-tenant access, an unapproved mutation, duplicate mutation, or missing audit/receipt pauses state changes.

## 5. End with a decision

Write down what can ship, what remains read-only, who owns each unresolved dependency, and what evidence would change the decision. Preserve a short failure example alongside the successful demo. This makes the next engineering step reviewable by both the operator and the implementation team.
