# Domain invariants and terminology

**AI proposes. Evidence explains. Human decides.**

These semantics apply to the current PoC and future Option B work. Future terms
do not imply implemented models, scores, APIs, or lifecycle operations.

## Terms

| Term | Meaning and current status |
| --- | --- |
| Source Finding | A source-specific observation before canonical normalization, such as a scanner finding or incident record. Explicit connectors wrap those records in the shared `SourceObservation` boundary; Semgrep, Incident, and Git/SATD may still use legacy loader paths. Not every source has migrated to the explicit Connector contract. `SourceObservation` is not a canonical Signal |
| Signal | A canonical source-observed event with affected asset, source identity, detection time, type, optional severity and Evidence references |
| Evidence | Traceable support for an observation: source, reference, capture time and optional URI; it supports assessment without validating debt |
| Candidate | A deterministic problem hypothesis for a canonical asset, referencing Signals and Evidence and carrying correlation rationale; not validated debt |
| TechnicalDebt | Future human-validated debt governed through a lifecycle; no lifecycle implementation or table exists today |
| Enterprise Context | Asset identity/type, criticality/lifecycle, recorded teams/ownerships, relationships, incidents and dependency context that help interpret a Candidate |
| Criticality | The enterprise asset's importance classification; currently an asset attribute, not a Candidate risk score |
| Risk | Assessment of potential adverse outcomes and uncertainty; no Candidate risk assessment/score is implemented |
| Effort | Estimated work/resources for an intervention; no Candidate effort estimate is implemented |
| Reachability | Deterministic connectivity in the persisted dependency graph; reachable dependents are not guaranteed outage or causal impact |

`NormalizedSignal` currently bundles one Signal and a nonempty Evidence set
whose identifiers exactly match the Signal's Evidence references. Candidate
requires nonempty Signal/Evidence references, a canonical asset, hypothesis and
rationale. These structural integrity checks are not human lifecycle validation.

## Transitions and decision boundary

```text
CURRENT: Source Finding → normalization → Signal + Evidence
                        → deterministic correlation → Candidate

FUTURE:  Candidate → human validation → TechnicalDebt (if validated)
```

Candidate creation does not automatically create TechnicalDebt. Current
correlation groups by canonical asset and problem family. Its incident recurrence
heuristic does not establish a common root cause. Human validation and subsequent
debt lifecycle operations remain future work.

## Invariants

- **Source Finding != Signal:** canonical meaning must be established by normalization.
- **Signal != Candidate:** an observation is distinct from a correlated hypothesis.
- **Candidate != TechnicalDebt:** correlation does not validate debt.
- **Evidence != Validation:** traceability and supporting facts do not confer approval.
- **Criticality != Risk:** asset importance alone is not an adverse-outcome assessment.
- **Risk != Effort:** potential harm and remediation work are separate dimensions.
- **Relationship / reachability != causality:** graph connections do not prove root cause or impact.
- **Suggested Team != validated ownership:** a suggestion cannot assign responsibility; current APIs expose recorded enterprise ownerships, not suggested teams.
- **Agent assessment != authorization:** a future agent's judgment cannot approve execution.
- **Tool availability != permission:** discovering a future tool does not authorize its use.
- **Verification != closure:** checking an execution result does not close debt.

Authorized humans retain critical lifecycle decisions, including validation,
risk acceptance and closure. No agent currently implements these decisions.
Future L4 execution is **TARGET only**:

```text
Agent prepares → Human approves → Policy checks → Executor executes
               → Result verified → Audit persisted
```

See the [architecture overview](../architecture/overview.md) for current code
boundaries and deferred contracts.
