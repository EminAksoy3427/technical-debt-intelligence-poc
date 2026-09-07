# Domain invariants and terminology

**AI proposes. Evidence explains. Human decides.**

These semantics apply to the current PoC and future Option B work. Future terms
do not imply implemented models, scores, APIs, or lifecycle operations beyond
the current Day 5 governed-action slice.

## Terms

| Term | Meaning and current status |
| --- | --- |
| Source Finding | A source-specific observation before canonical normalization, such as a scanner finding or incident record. Explicit connectors wrap those records in the shared `SourceObservation` boundary; Semgrep, Incident, and Git/SATD may still use legacy loader paths. Not every source has migrated to the explicit Connector contract |
| SourceObservation | Connector-owned acquisition envelope around a source-specific record. It is not a canonical Signal |
| Signal | A canonical source-observed event with affected asset, source identity, detection time, type, optional severity and Evidence references |
| Evidence | Traceable support for an observation: source, reference, capture time and optional URI; it supports assessment without validating debt |
| Candidate | A deterministic problem hypothesis for a canonical asset, referencing Signals and Evidence and carrying correlation rationale; not validated debt. Governance state and revision are derived from HumanDecision history; Candidates have no status/revision columns |
| HumanDecision | An immutable human governance decision (`VALIDATE`, `REJECT`, `REQUEST_INFO`) with server-owned actor attribution. It is not a Structured Assessment |
| TechnicalDebt | A REGISTERED provenance record created only by a valid Human `VALIDATE`. It is not remediation approval, scheduled work, or resolution. Risk, effort, owner, target date, and closure are not implemented |
| StructuredAssessment | Agent Investigation output grounded in evidence/tool references. It recommends; it does not authorize |
| Human Validation | The Day 4 human command that classifies a Candidate. It is not L4 Action Approval |
| ActionProposal | Immutable L3 preview of one exact `CREATE_GITHUB_ISSUE` mutation. Server-prepared. Not authorization, not execution, and not an "active proposal" lifecycle object |
| ActionApproval | Immutable L4 human approval of one ActionProposal identity plus payload fingerprint. Existence is not policy ALLOW and is not execution |
| ActionPolicyDecision | Append-only dedicated L4 action-execution policy evaluation. Separate from Agent Tool Policy. Not AI reasoning |
| ActionExecution | One persisted attempt to perform one ActionProposal. Statuses: `IN_PROGRESS`, `SUCCEEDED`, `FAILED`, `UNKNOWN` |
| ActionVerification | One immutable GET-only read-back of a persisted execution. Results: `PASS`, `FAIL`, `UNAVAILABLE`. Not execution and not TechnicalDebt closure |
| GitHub READ Connector | Acquisition-plane GET connector. External source → `SourceObservation`. Does not write and does not verify action executions |
| GitHub Issue Executor | Action-plane writer. One POST create-issue attempt with a dedicated server-owned token. No mutation retry |
| GitHub Issue Verifier | Action-plane GET-only read-back. Exact issue read and reconciliation-marker search. No POST |
| Enterprise Context | Asset identity/type, criticality/lifecycle, recorded teams/ownerships, relationships, incidents and dependency context that help interpret a Candidate |
| Criticality | The enterprise asset's importance classification; currently an asset attribute, not a Candidate or TechnicalDebt risk score |
| Risk | Assessment of potential adverse outcomes and uncertainty; no risk assessment/score is implemented |
| Effort | Estimated work/resources for an intervention; no effort estimate is implemented |
| Reachability | Deterministic connectivity in the persisted dependency graph; reachable dependents are not guaranteed outage or causal impact |

`NormalizedSignal` currently bundles one Signal and a nonempty Evidence set
whose identifiers exactly match the Signal's Evidence references. Candidate
requires nonempty Signal/Evidence references, a canonical asset, hypothesis and
rationale. These structural integrity checks are not human lifecycle validation.

## Transitions and decision boundary

```text
CURRENT: Source Finding / SourceObservation → normalization → Signal + Evidence
                        → deterministic correlation → Candidate
                        → Human Validation
                             VALIDATE     → VALIDATED + exactly one REGISTERED TechnicalDebt
                             REJECT       → REJECTED, no TechnicalDebt
                             REQUEST_INFO → INFORMATION_REQUESTED, no TechnicalDebt
                        → L3 Action Preparation → immutable ActionProposal
                        → Human L4 Approval → ActionApproval
                        → dedicated Action Execution Policy → ActionPolicyDecision
                        → ActionExecution → external GitHub create (one attempt)
                        → ActionVerification → persisted audit trail

NOT IMPLEMENTED: TechnicalDebt closure / RESOLVED, reopen, PR creation,
                 code patch execution, Jira/ServiceNow writers
```

Candidate creation does not automatically create TechnicalDebt. Current
correlation groups by canonical asset and problem family. Its incident recurrence
heuristic does not establish a common root cause. `MERGE` is deferred.
TechnicalDebt remains `REGISTERED` after a verified GitHub issue exists.

## Source, Signal, and Candidate

- **Source Finding != Signal:** canonical meaning must be established by normalization.
- **SourceObservation != Signal:** acquisition wrapping is not canonical meaning.
- **Signal != Candidate:** an observation is distinct from a correlated hypothesis.
- **Candidate != TechnicalDebt:** correlation does not validate debt. TechnicalDebt can result only from valid Human `VALIDATE` authority.
- **Evidence != Validation:** traceability and supporting facts do not confer approval.
- **Criticality != Risk:** asset importance alone is not an adverse-outcome assessment.
- **Risk != Effort:** potential harm and remediation work are separate dimensions.
- **Relationship / reachability != causality:** graph connections do not prove root cause or impact.
- **Suggested Team != validated ownership:** a suggestion cannot assign responsibility; current APIs expose recorded enterprise ownerships, not suggested teams.

## Human Validation and TechnicalDebt

- **StructuredAssessment != HumanDecision:** agent output is not a human governance decision.
- **Human Validation != L4 Action Approval:** classifying a Candidate is not authorizing an external write.
- **TechnicalDebt REGISTERED != remediation approved.**
- **TechnicalDebt REGISTERED != work scheduled.**
- **TechnicalDebt REGISTERED != resolved.**

Human Validation uses server-owned opaque actor attribution. It is not
enterprise identity, SSO, or reviewer RBAC. No Agent can perform Human
Validation or L4 decisions. Human Validation is a server-owned application
command, not an Agent Tool.

## Agent investigation authority

- **Agent assessment != authorization:** an agent's judgment cannot approve execution.
- **Policy ALLOW != human approval:** Agent Tool Policy records permission to use a READ tool; it is not Human Validation or L4 approval.
- **Tool availability != permission:** discovering a tool does not authorize its use.

There is no Agent WRITE tool. The GitHub Issue Executor is an application-owned
action-plane adapter, not an Agent Tool.

## L3 Action Preparation

```text
TechnicalDebt REGISTERED → immutable ActionProposal (CREATE_GITHUB_ISSUE)
```

ActionProposal is server-prepared. The client does not choose target
repository, title, body, fingerprint, reconciliation marker, or actor.
`action_proposal_id` is proposal/attempt identity. Multiple immutable proposals
per TechnicalDebt are allowed. There is no "active proposal" domain concept.

Persisted proposal truth:

- `action_proposal_id`
- `technical_debt_id`
- `action_type`
- target repository owner and name
- title
- body
- `payload_fingerprint`
- `reconciliation_marker`
- `prepared_by`
- `created_at`

- **ActionProposal != authorization.**
- **PREPARED != APPROVED.**
- **Action Proposal != Action Execution.**

## Logical action identity

The cross-proposal logical GitHub CREATE identity is:

```text
technical_debt_id + action_type = CREATE_GITHUB_ISSUE
```

Multiple proposals may exist. Only one live logical GitHub CREATE may occupy
the slot. Live occupancy statuses:

- `IN_PROGRESS`
- `UNKNOWN`
- `SUCCEEDED`

`FAILED` releases the slot for a new proposal. `SUCCEEDED` permanently occupies
it. `UNKNOWN` does not release it. The same proposal is not executed twice.

## L4 approval, policy, and execution

Current governed action flow:

```text
Human approves. Policy authorizes. Executor performs. Verification checks. Audit records.
```

- **ActionApproval** binds `action_proposal_id` + `payload_fingerprint` +
  server-owned `actor_reference`. The client sends only
  `expected_payload_fingerprint`. `actor_reference` is opaque audit
  attribution, not enterprise IAM, SSO, or RBAC.
- **Approval existence != policy ALLOW.**
- **Policy ALLOW != successful external execution.**
- **APPROVED != EXECUTED.**
- **EXECUTED != VERIFIED.**
- **VERIFIED != CLOSED.**
- **Frontend button state != authorization.**

Dedicated Action Execution Policy evaluates server-owned facts: execution
enabled, action type, repository allowlist, approval existence, fingerprint
consistency, and executor readiness. Current reason codes:

- `EXECUTION_DISABLED`
- `ACTION_TYPE_NOT_ALLOWED`
- `REPOSITORY_NOT_ALLOWLISTED`
- `APPROVAL_MISSING`
- `FINGERPRINT_MISMATCH`
- `POLICY_ALLOWED`

DENY persists the decision and results in zero external execution. Policy is
deterministic rule evaluation, not AI reasoning. It is not Agent Tool Policy.

ActionExecution statuses:

- `IN_PROGRESS` — claimed, external call not yet finalized
- `SUCCEEDED` — definite created GitHub issue reference
- `FAILED` — definite failure (`EXTERNAL_REJECTED` or `NOT_SENT`)
- `UNKNOWN` — external outcome is uncertain (`TRANSPORT_UNKNOWN`)

`UNKNOWN` is not failure. `UNKNOWN` occupies the logical action slot. There is
no blind POST retry.

## GitHub boundaries

- **GitHub READ Connector != GitHub Issue Executor.**
- **GitHub Issue Executor != GitHub Issue Verifier.**

| Plane | Component | Effect |
| --- | --- | --- |
| Acquisition | GitHub READ Connector | GET-only source → `SourceObservation` |
| Action write | GitHub Issue Executor | one POST create issue; dedicated server-owned token; no mutation retry |
| Action read-back | GitHub Issue Verifier | GET-only exact issue read and marker search; no POST |

## Verification and reconciliation

- **Verification != execution.**
- **Verification != closure.**

ActionVerification results:

- `PASS` — external issue matches approved proposal semantics
- `FAIL` — read-back completed but persisted approved semantics differ
- `UNAVAILABLE` — external verification could not currently complete

The persisted ActionProposal is comparison authority. Comparison uses approved
stable facts: target repository context, persisted external reference, issue vs
pull request, exact reconciliation marker, and a reconstructed canonical
fingerprint from observed title/body. Unstable GitHub metadata is not compared.
Raw GitHub responses are not persisted.

For `UNKNOWN` and crash-window `IN_PROGRESS`: do not POST again. Search/read by
the persisted reconciliation marker. Only exact marker proof may recover
external identity. `UNKNOWN` may transition to `SUCCEEDED` only through marker
proof. Marker absent: `UNKNOWN` remains `UNKNOWN`. Multiple exact matches:
ambiguous / unresolved. There is no invented `UNKNOWN` → `FAILED` transition.

The immutable marker embedded in the final issue body is conceptually
`tdiq-action-proposal:{action_proposal_id}`. It is reconciliation identity, not
authentication or authorization.

## Secrets and frontend authority

The GitHub execution-plane credential is server-owned `SecretStr`. It is never
persisted on ActionProposal, ActionApproval, ActionPolicyDecision,
ActionExecution, or ActionVerification, and never returned through API or
frontend.

Frontend TechnicalDebt Detail sends intent only. There is no automatic
approval → execute, execution → verify, or POST retry. Disabled buttons are
UX, not permission enforcement.
