# Core Concepts

The system deliberately separates source observations, supporting facts, governance
decisions, authorization, external execution, and confirmation of the result.

| Concept | Definition | Why it matters |
|---|---|---|
| Source | A system or controlled dataset from which facts are acquired, such as Semgrep output, Git history, incidents, dependency data, or GitHub Issues. | A source supplies observations, not lifecycle authority. |
| Connector | A registered acquisition boundary with declared identity, version, transport, source system, and read-only status. | It isolates source access from canonical interpretation and execution. |
| Signal | A source-observed event with a source-independent type and affected canonical asset. | It creates a common factual model without declaring technical debt. |
| Evidence | A timestamped source reference that supports a Signal or investigation claim. | Reviewers and assessments need inspectable support. |
| Provenance | The source system and stable source record identity from which an observation originated. | It makes origin traceable and supports de-duplication. |
| Candidate | A deterministic problem hypothesis joining one or more Signals and Evidence items to a canonical asset. | It is the unit of investigation and human review, not validated debt. |
| Enterprise Asset | A controlled application, service, or repository with identity, name, criticality, and lifecycle state. | It anchors findings to managed technical systems. |
| Enterprise Context | Ownership, direct relationships, direct incidents, and derived dependency reachability around a Candidate's asset. | It provides organizational and operational facts without inferring causality or risk. |
| Technical Debt | A persistent lifecycle entity created only by a human `VALIDATE` decision. | It marks entry into governed management. The current lifecycle state is `REGISTERED`. |
| Agent Investigation | A bounded run in which a configured provider uses allowed read tools to produce a structured, grounded assessment or abstain. | It assists review while keeping authority outside the model. |
| Agent Tool | A registered, typed capability checked for candidate scope, effect, risk, and required scopes before execution. | It limits what an investigation can observe or do. Current tools are read-only. |
| Human Validation | An authoritative `VALIDATE`, `REJECT`, or `REQUEST_INFO` decision appended to Candidate governance history. | It controls whether a Candidate becomes TechnicalDebt. |
| Policy Decision | A deterministic `ALLOW` or `DENY` result based on trusted persisted and server-owned inputs. | It prevents approval from being treated as sufficient execution authority. |
| Governed Action | The controlled sequence of immutable proposal, exact-payload approval, policy evaluation, execution, and verification. | It makes external change explicit and reviewable. |
| Executor | A dedicated action-plane component that performs an authorized external mutation. | Mutation authority remains separate from Connectors, the agent, and policy. |
| Verification | A separate read-back comparison of external state with the approved proposal; it can also reconcile an uncertain execution. | A request or successful response is not enough to establish external truth. |
| Audit Trail | Persisted AgentRuns, tool executions, tool-policy decisions, human decisions, proposals, approvals, action-policy decisions, executions, and verifications. | It preserves who or what decided, acted, and observed each stage. |

## Important Distinctions

### Signal vs Technical Debt

A Signal is an observation such as a Semgrep `MISSING_TIMEOUT` finding. TechnicalDebt
is created only after the related Candidate receives a human `VALIDATE` decision.

### Evidence vs Provenance

Evidence is the supporting reference—for example, a repository path, location, rule,
and finding message. Provenance is the stable origin pair, such as source system
`semgrep` and its exact source-record identifier.

### Candidate vs Technical Debt

A Candidate is a correlated hypothesis and may remain pending, be rejected, or require
more information. Validated TechnicalDebt is a separate persistent record linked to
the Candidate and the HumanDecision that created it.

### AI Recommendation vs Human Decision

The agent may return a supported assessment, a recommendation, uncertainties, or an
abstention. None changes Candidate governance. Only a server-authorized human command
can validate, reject, or request information.

### Human Approval vs Policy Authorization

An ActionApproval records that a human approved one immutable proposal fingerprint.
Immediately before execution, policy separately checks that approval, fingerprint,
action type, configured target repository, execution feature state, and executor
availability.

### Connector vs Executor

The Dependency Lifecycle and GitHub Issues Connectors acquire source data and are
declared read-only. The GitHub Issue executor is a separate action-plane boundary that
can create an Issue only after policy authorization.

### Execution vs Verification

Execution records the attempt and its immediate outcome. Verification uses a dedicated
GET-only port to compare the external Issue with the approved proposal. A
`SUCCEEDED` execution without a `PASS` verification is successful execution, not
verified execution.

## Related Documentation

- [System Overview](system-overview.md)
- [End-to-End Flow](end-to-end-flow.md)
- [Security and Trust Boundaries](../02-architecture/security-and-trust-boundaries.md)
- [Human Validation and Lifecycle](../05-agent-and-governance/human-validation-and-lifecycle.md)
