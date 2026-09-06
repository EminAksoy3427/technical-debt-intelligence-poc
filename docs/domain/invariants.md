# Domain invariants and terminology

**AI proposes. Evidence explains. Human decides.**

These semantics apply to the current PoC and future Option B work. Future terms
do not imply implemented models, scores, APIs, or lifecycle operations beyond
the Day 4 Human Validation slice.

## Terms

| Term | Meaning and current status |
| --- | --- |
| Source Finding | A source-specific observation before canonical normalization, such as a scanner finding or incident record. Explicit connectors wrap those records in the shared `SourceObservation` boundary; Semgrep, Incident, and Git/SATD may still use legacy loader paths. Not every source has migrated to the explicit Connector contract |
| SourceObservation | Connector-owned acquisition envelope around a source-specific record. It is not a canonical Signal |
| Signal | A canonical source-observed event with affected asset, source identity, detection time, type, optional severity and Evidence references |
| Evidence | Traceable support for an observation: source, reference, capture time and optional URI; it supports assessment without validating debt |
| Candidate | A deterministic problem hypothesis for a canonical asset, referencing Signals and Evidence and carrying correlation rationale; not validated debt. Governance state and revision are derived from HumanDecision history; Candidates have no status/revision columns |
| HumanDecision | An immutable human governance decision (`VALIDATE`, `REJECT`, `REQUEST_INFO`) with server-owned actor attribution. It is not a Structured Assessment |
| TechnicalDebt | A REGISTERED provenance record created only by a valid Human `VALIDATE` in the current Day 4 lifecycle. It is not remediation approval, scheduled work, or resolution. Risk, effort, owner, target date, verification, and closure are not implemented |
| StructuredAssessment | Agent Investigation output grounded in evidence/tool references. It recommends; it does not authorize |
| Human Validation | The Day 4 human command that classifies a Candidate. It is not L4 Action Approval |
| Action Proposal | Future L3 preparation of a governed action. Not implemented |
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

FUTURE:  ActionProposal / L3 → L4 approval and execution → verification → closure
```

Candidate creation does not automatically create TechnicalDebt. Current
correlation groups by canonical asset and problem family. Its incident recurrence
heuristic does not establish a common root cause. `MERGE` is deferred.
Subsequent debt lifecycle operations remain future work.

## Invariants

- **Source Finding != Signal:** canonical meaning must be established by normalization.
- **SourceObservation != Signal:** acquisition wrapping is not canonical meaning.
- **Signal != Candidate:** an observation is distinct from a correlated hypothesis.
- **Candidate != TechnicalDebt:** correlation does not validate debt. TechnicalDebt can result only from valid Human `VALIDATE` authority in the current Day 4 lifecycle.
- **Evidence != Validation:** traceability and supporting facts do not confer approval.
- **StructuredAssessment != HumanDecision:** agent output is not a human governance decision.
- **Agent assessment != authorization:** an agent's judgment cannot approve execution.
- **Policy ALLOW != human approval:** runtime policy records permission to use a READ tool; it is not Human Validation or L4 approval.
- **Human Validation != L4 Action Approval:** classifying a Candidate is not authorizing execution.
- **Action Proposal != Action Execution:** preparing a future action is not performing it.
- **Criticality != Risk:** asset importance alone is not an adverse-outcome assessment.
- **Risk != Effort:** potential harm and remediation work are separate dimensions.
- **TechnicalDebt REGISTERED != remediation approved / work scheduled / resolved.**
- **Relationship / reachability != causality:** graph connections do not prove root cause or impact.
- **Suggested Team != validated ownership:** a suggestion cannot assign responsibility; current APIs expose recorded enterprise ownerships, not suggested teams.
- **Tool availability != permission:** discovering a future tool does not authorize its use.
- **Verification != closure:** checking an execution result does not close debt.

Lifecycle authority remains human-governed. Current Human Validation uses
server-owned opaque actor attribution. It is not enterprise identity or
reviewer authorization. No Agent can perform Human Validation or L4 decisions.
Human Validation is a server-owned application command, not an Agent Tool.
Future L4 execution is **TARGET only**:

```text
Agent prepares → Human approves → Policy checks → Executor executes
               → Result verified → Audit persisted
```

See the [architecture overview](../architecture/overview.md) for current code
boundaries and deferred contracts.
