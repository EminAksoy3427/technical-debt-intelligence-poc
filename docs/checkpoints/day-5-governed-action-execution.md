# Day 5 acceptance checkpoint — Governed Action Execution

Baseline before this documentation package: **eb1c1ff**
(`eb1c1ff35a791310a8d40a500952214a4a17d6d3`).

This checkpoint records Day 5 implementation through the frontend workbench.
It adds no product capability and does not start Day 6.

## Purpose

Align repository documentation with the implemented and tested Day 5 system:
REGISTERED TechnicalDebt can receive a server-prepared immutable GitHub issue
ActionProposal, human L4 approval, dedicated action-execution policy, one-shot
GitHub create, GET-only verification/reconciliation, and a persisted audit
trail.

Human approves. Policy authorizes. Executor performs. Verification checks.
Audit records. AI does not autonomously authorize or perform external writes.

## Authorized baseline entering Day 5

Accepted frontend workspace before Day 5 action packages:

```text
901741f feat(frontend): complete technical debt governance workspace redesign
```

Day 4 documentation close immediately before that workspace:

```text
7432340 docs: align Day 4 governance documentation
```

Day 5 implementation then proceeded on `main`.

## Packages completed

| Package | Commit | Subject |
| --- | --- | --- |
| 2 | `db0ab0d` (`db0ab0dbd45a7ba4177a50cdf7b8212365ba26a1`) | `feat: add immutable L3 action proposal preparation` |
| 3 | `2edc88f` (`2edc88f37ef923e0b62cf09ec089cf5002905682`) | `feat: expose L3 action proposal preview` |
| 4 | `7b8d67f` (`7b8d67f6e7478eb7559e3f161fda485bfaaedd5f`) | `feat: add L4 action approval and execution policy` |
| 5 | `7f4f075` (`7f4f075aa21fd4a407488a053d942636b8560977`) | `feat: add governed GitHub issue execution` |
| 6 | `f35c9cb` (`f35c9cbd6c80b0976b3070fd0d5de2a643a230a7`) | `feat: add action execution verification and reconciliation` |
| 7 | `eb1c1ff` (`eb1c1ff35a791310a8d40a500952214a4a17d6d3`) | `feat(frontend): add governed action execution workbench` |
| 8 | not committed | documentation alignment (this checkpoint) |

Exact `git log` chain at documentation baseline:

```text
eb1c1ff feat(frontend): add governed action execution workbench
f35c9cb feat: add action execution verification and reconciliation
7f4f075 feat: add governed GitHub issue execution
7b8d67f feat: add L4 action approval and execution policy
2edc88f feat: expose L3 action proposal preview
db0ab0d feat: add immutable L3 action proposal preparation
901741f feat(frontend): complete technical debt governance workspace redesign
7432340 docs: align Day 4 governance documentation
```

## Final architecture

Architecture remains **Option B**: Extensible Modular Monolith + Ports &
Adapters + Explicit Extension Contracts + Governed Agent Runtime +
async-ready seams + MSSQL/Alembic system of record. This is not
microservices. Kafka, RabbitMQ, Celery, and Kubernetes are not present.

Day 5 adds an application-owned action plane beside acquisition and Agent
Investigation:

```text
READ / investigation plane
  AgentRuntime → Tool Registry → Agent Tool Policy → Candidate READ tools

Human governance command plane
  apply_human_validation → REGISTERED TechnicalDebt

Governed action plane
  ActionProposal → ActionApproval → Action Execution Policy
    → GitHub Issue Executor → GitHub Issue Verifier → audit persistence
```

The GitHub Issue Executor is not an Agent WRITE tool. The GitHub READ
connector remains acquisition-only.

## L3 preparation

```text
TechnicalDebt REGISTERED → immutable ActionProposal (CREATE_GITHUB_ISSUE)
```

Preparation is server-owned. The client sends no body and cannot choose
target repository, title, body, fingerprint, reconciliation marker, or actor.
Multiple immutable proposals per TechnicalDebt are allowed.
`action_proposal_id` is proposal/attempt identity. There is no "active
proposal" concept.

Persisted proposal truth includes `action_proposal_id`, `technical_debt_id`,
`action_type`, target repository, title, body, `payload_fingerprint`,
`reconciliation_marker`, `prepared_by`, and `created_at`.

PREPARED is not APPROVED. ActionProposal is not authorization.

## L4 approval

ActionApproval is immutable / append-only governance evidence. It binds:

```text
action_proposal_id + payload_fingerprint + server-owned actor_reference
```

The client sends only `expected_payload_fingerprint`. `actor_reference` is
opaque audit attribution. It is not enterprise IAM, SSO, or RBAC.

Human Validation and L4 Action Approval are separate governance events.
`HUMAN_GOVERNANCE_ENABLED` does not enable L4.
`HUMAN_ACTION_EXECUTION_ENABLED` is the L4 capability seam.

Approval existence is not policy ALLOW. APPROVED is not EXECUTED.

## Execution policy

Dedicated Action Execution Policy is separate from Agent Tool Policy. It
evaluates server-owned facts in a fixed order:

1. execution enabled and executor ready → otherwise `EXECUTION_DISABLED`
2. action type `CREATE_GITHUB_ISSUE` → otherwise `ACTION_TYPE_NOT_ALLOWED`
3. repository allowlist → otherwise `REPOSITORY_NOT_ALLOWLISTED`
4. approval presence → otherwise `APPROVAL_MISSING`
5. fingerprint consistency → otherwise `FINGERPRINT_MISMATCH`
6. otherwise `ALLOW` / `POLICY_ALLOWED`

Policy decisions are persisted. DENY results in zero external execution.
Policy is deterministic rule evaluation, not AI reasoning.

## Executor boundary

`HttpGitHubIssueExecutor` (`backend/app/infrastructure/github_issue_executor.py`)
performs one POST to create a GitHub issue. Transport retries are zero. A
dedicated server-owned `SecretStr` token is used. Missing token makes the
executor not ready; policy DENY with `EXECUTION_DISABLED` occurs before any
network call.

This is not the GitHub READ connector and not the GitHub Issue Verifier.

## Transaction protocol

Package 5 protocol:

```text
Phase A DB transaction
  TechnicalDebt lock
  → proposal load
  → duplicate / logical occupancy check
  → approval load
  → policy evaluation / persistence
  → IN_PROGRESS execution persistence
  → COMMIT

NO DB transaction
  → one external GitHub create attempt

Phase B DB transaction
  → finalize SUCCEEDED / FAILED / UNKNOWN
  → COMMIT
```

The database transaction is never held across external HTTP. This is not a
distributed transaction and does not claim exactly-once delivery.

## Idempotency / logical occupancy

Same proposal is not executed twice. A later POST for the same proposal
returns the persisted ActionExecution (HTTP 200) without a second GitHub POST.

Cross-proposal logical identity:

```text
technical_debt_id + action_type = CREATE_GITHUB_ISSUE
```

Live occupancy statuses: `IN_PROGRESS`, `UNKNOWN`, `SUCCEEDED`.
`FAILED` releases the slot for a new proposal. `SUCCEEDED` permanently
occupies it. `UNKNOWN` does not release it.

MSSQL enforces live occupancy with filtered unique index
`uq_action_executions_live_logical_action`. This is not PostgreSQL.

## UNKNOWN semantics

`UNKNOWN` means the external outcome is uncertain (`TRANSPORT_UNKNOWN`).
It is not failure. It occupies the logical action slot. There is no blind
POST retry. Do not invent `UNKNOWN` → `FAILED`.

`FAILED` is reserved for definite failure (`EXTERNAL_REJECTED` or `NOT_SENT`).

## Verification

ActionVerification is a separate GET-only read-back:

- `PASS` — external issue matches approved proposal semantics
- `FAIL` — read-back completed but persisted approved semantics differ
- `UNAVAILABLE` — external verification could not currently complete

Verification is not execution and not TechnicalDebt closure. `FAILED`
executions are not verifiable. Comparison uses persisted ActionProposal as
authority: target repository context, persisted external reference, issue vs
pull request, exact reconciliation marker, and reconstructed canonical
fingerprint. Unstable GitHub metadata is not compared. Raw GitHub responses
are not persisted.

## Reconciliation

For `UNKNOWN` and crash-window `IN_PROGRESS`, do not POST again. Search/read
by the persisted reconciliation marker. Only exact marker proof may recover
external identity. `UNKNOWN` may become `SUCCEEDED` only through marker proof.
Marker absent: `UNKNOWN` remains `UNKNOWN` (HTTP 409 unresolved, no status
rewrite to `FAILED`). Multiple exact matches: ambiguous / unresolved.

The immutable marker embedded in the issue body is conceptually
`tdiq-action-proposal:{action_proposal_id}`. It is reconciliation identity,
not authentication or authorization.

## Frontend vertical slice

`/technical-debts/[id]` current flow:

```text
provenance
  → Action Preparation
  → L4 Human Approval
  → Execution
  → External Reference
  → Verification
  → Audit Trail
```

Separate controls: Prepare GitHub Issue, Approve External Action, Execute
Approved Action, Verify External Action. Frontend sends intent only. No
automatic approval → execute, execution → verify, or POST retry. 409 refreshes
persisted truth once. Successful mutation plus failed refresh preserves the
returned persisted resource. Disabled buttons are not permission enforcement.

Package 7 browser smoke rendered the workbench and did not click mutation
actions.

## Audit

The frontend audit timeline is derived from persisted backend records:

- TechnicalDebt
- ActionProposal
- ActionApproval
- ActionPolicyDecision
- ActionExecution
- ActionVerification

No browser-only audit events. No generic event store. No raw
chain-of-thought. No secrets.

## Security boundaries

- Client cannot submit actor, token, repository, title, body, or policy
  decision for preparation/execution/verification.
- Approval body is fingerprint-only.
- Agent assessment is not authorization.
- Tool availability is not permission.
- Frontend button state is not authorization.
- GitHub READ connector is not write authority.

## Secrets

GitHub execution-plane credential is server-owned `SecretStr`
(`GITHUB_ISSUE_EXECUTOR_TOKEN`). Verification reuses that same secret for
GET. It is never persisted on action records and never returned through API
or frontend. Do not put real tokens in documentation.

## MSSQL persistence

Repository head: **`20260907_04`**.

```text
20260907_01 action_proposals
20260907_02 action_approvals / action_policy_decisions
20260907_03 action_executions
20260907_04 action_verifications
```

Append-only / immutable intent applies to proposals, approvals, policy
decisions, and verifications. Executions are claimed `IN_PROGRESS` then
finalized; the only later success rewrite is marker-proven
`UNKNOWN` → `SUCCEEDED`.

## API surface

```text
POST /api/v1/technical-debts/{id}/action-proposals
POST /api/v1/technical-debts/{id}/action-proposals/{proposal}/approvals
POST /api/v1/technical-debts/{id}/action-proposals/{proposal}/executions
POST /api/v1/technical-debts/{id}/action-proposals/{proposal}/executions/{execution}/verifications
```

GET TechnicalDebt detail includes `action_proposals`, `action_approvals`,
`action_policy_decisions`, `action_executions`, and `action_verifications`.
Preparation, execution, and verification have no body. Approval body is
`expected_payload_fingerprint` only.

Confirmed status codes from the API implementation include 201 create, 200
existing execution, 403 policy/approval/verification unavailable or denied,
409 occupancy/stale/unresolved, 404 missing identities, 422 unsupported body,
and 503 unconfigured preparation/approval.

## Tests / proof

These are package-stage recorded results. They were not re-run as one combined
Day 5 suite for this documentation package.

| Stage | Recorded result |
| --- | --- |
| Package 5 | focused, deterministic, and MSSQL execution suites recorded in that implementation report |
| Package 6 focused | **42 passed** after the final reconciliation mini-fix |
| Package 6 deterministic backend | **791 passed** in that implementation report |
| Package 6 MSSQL | verification/reconciliation proof, including concurrent UNKNOWN reconcile |
| Package 7 focused frontend | **56 passed** |
| Package 7 full frontend | **44 files / 321 tests passed**; typecheck passed; production build passed |
| Package 7 focused backend | **11 passed** |
| Package 7 browser smoke | **passed**; no mutation clicked |

Do not treat these figures as a newly executed aggregate in Package 8.
If a later run produces a different total, prefer that later log.

## Real external write status

The governed GitHub write **capability exists**.

Package development and tests did **not** perform a real GitHub write.
Browser smoke did **not** click mutation actions.
No repository evidence in this checkpoint proves that a live GitHub issue was
created.

Keep "capability implemented" separate from "live demo executed".

## Known environment limitations

- Local Semgrep executable may be absent. That environment-specific failure
  is separate from product regressions in the governed action plane.
- Local `.env` may select the OpenAI investigation provider.
- Human actor and L4 execution remain PoC server configuration only.
- GitHub READ connector remains public unauthenticated GET.
- Execution-plane token, when present, is a local secret and must not be
  committed.

## Explicit non-goals

Still **not** implemented:

- TechnicalDebt closure / `RESOLVED` lifecycle
- reopen
- risk scoring
- effort scoring
- priority
- validated owner assignment
- due date / SLA
- PR creation
- code patch execution
- automatic write retry
- Jira write executor
- ServiceNow write executor
- enterprise IAM / SSO / RBAC
- generic workflow engine
- Kafka
- RabbitMQ
- Celery
- Kubernetes
- dynamic plugin marketplace

## Final commit chain

Implementation HEAD entering this documentation package:

```text
eb1c1ff feat(frontend): add governed action execution workbench
```

Package 8 must not claim its own commit hash until a later documentation
commit exists.

## Day 5 exit criteria

| Item | Result |
| --- | --- |
| Human Validation remains distinct from L4 Action Approval | **PASS** |
| ActionProposal is immutable server-prepared preview | **PASS** |
| Client cannot choose repository/title/body/actor | **PASS** |
| Approval binds proposal + fingerprint + server actor | **PASS** |
| Dedicated action policy is separate from Agent Tool Policy | **PASS** |
| Policy DENY produces zero external execution | **PASS** |
| GitHub READ connector is not the executor or verifier | **PASS** |
| DB transaction is not held across GitHub HTTP | **PASS** |
| Same proposal is not executed twice | **PASS** |
| FAILED releases logical occupancy; UNKNOWN does not | **PASS** |
| UNKNOWN is not described or implemented as FAILED | **PASS** |
| Verification is GET-only and does not close TechnicalDebt | **PASS** |
| Marker proof is the only UNKNOWN → SUCCEEDED path | **PASS** |
| Secrets are not persisted or returned | **PASS** |
| Frontend sends intent only; no auto-chaining or POST retry | **PASS** |
| Audit trail is persisted backend records only | **PASS** |
| TechnicalDebt remains REGISTERED | **PASS** |
| Real GitHub write not claimed as executed | **PASS** |
| No microservices / Kafka / Celery / Kubernetes claim | **PASS** |

## Next possible steps

Do not implement these in Day 5.

Possible later directions, outside this checkpoint:

- a controlled live GitHub write demonstration under explicit operator control
- TechnicalDebt closure / verification-informed lifecycle, if separately
  authorized
- additional action types such as PR creation
- enterprise identity, if a later slice requires it

See current-state detail in the
[architecture overview](../architecture/overview.md),
[API contract](../api-contract.md),
[database evolution](../database/evolution-and-migrations.md), and
[domain invariants](../domain/invariants.md).
