# Security and Trust Boundaries

This document describes the trust boundaries implemented by the Current PoC Baseline.
It is architecture documentation, not a production security assessment.

## Trust Model

External and controlled sources provide observations, not technical-debt truth.
Canonical facts are established through deterministic validation and mapping. Agent
output is advisory. Human decisions are authoritative only at the governance stage
for which the server grants authority, and an approved external action still requires
deterministic policy authorization. External completion is established only through a
separate verification result.

## Main Trust Boundaries

| Boundary | Risk | Current Control |
|---|---|---|
| External or controlled source -> acquisition | Malformed, unavailable, duplicated, or source-specific data may be treated as canonical. | Source adapters validate required fields and timestamps; Connector metadata declares source identity and read-only status; transport failures have typed outcomes or errors. |
| Acquisition -> canonical Signal | An observation may lose provenance or be overstated as debt. | Source-specific deterministic normalizers create stable identities and require matching, non-empty Evidence; Signal remains distinct from Candidate and TechnicalDebt. |
| Signals -> Candidate | Correlation may imply causality or validation. | Deterministic grouping uses canonical asset and exact problem family; recurring incidents require distinct observations, and the rationale explicitly avoids claiming common root cause. |
| Stored evidence -> agent | The model may receive facts outside the requested Candidate or unsupported context. | Database readers expose bounded Candidate views through three registered read tools; runtime authorization fixes the Candidate ID and grants only `candidate:read`. |
| Agent provider -> tool | A provider may request an unknown, malformed, excessive, risky, or out-of-scope operation. | Explicit tool registry, Pydantic argument/result validation, candidate scope, effect/risk/scope policy, iteration and call budgets, run/tool deadlines, and audited stop reasons. |
| Application -> AI provider | Provider choice, credentials, model output, or tool calls may bypass application controls. | Provider selection, model, key, and timeout are server-owned; the runtime depends on `InvestigationProvider` and validates provider steps and final structured assessment references. |
| AI recommendation -> human validation | Advisory output may be treated as authoritative debt state. | Agent modules do not call the human-validation service; validation is a separate API command and only `VALIDATE` creates TechnicalDebt. |
| Human input -> governance state | A client may claim another identity, use stale state, or request an illegal transition. | Actor identity and enablement come from server settings; commands carry an expected governance revision; transition and persistence checks fail on stale or invalid operations. |
| Human approval -> action policy | Approval may be stale, target a different payload, or be mistaken for authorization. | Approval is bound to the persisted SHA-256 proposal fingerprint; policy separately checks enablement, executor readiness, action type, allowlisted repository, approval presence, and fingerprint equality. |
| Policy -> executor | A denied, disabled, or unclaimed action may reach an external writer. | Execution calls the executor only after an `ALLOW`; a durable execution claim is persisted before the network call; missing executor configuration denies policy. |
| Executor -> GitHub | Credentials or retry behavior may create uncontrolled or duplicate mutations. | Token and target are server-owned, writes are disabled by default, the HTTP writer has explicit timeouts and zero automatic retries, and outcomes distinguish rejection, not-sent, and uncertainty. |
| GitHub result -> verified execution | A response or external reference may not match the approved action. | A separate GET-only verifier compares repository and issue reference, reconciliation marker, title, and canonical payload fingerprint; uncertain results reconcile only one unambiguous match. |

## Agent Boundary

The agent can read authorized Candidate evidence, dependency context, and enterprise
context through registered tools. It can return a structured supported assessment or
abstain, with grounded references, missing evidence, uncertainties, and a
recommendation.

The agent cannot create authoritative TechnicalDebt, perform human validation,
approve an action, bypass tool or execution policy, register arbitrary tools, select
server credentials or providers, or directly invoke the GitHub writer. A supported
claim must reference Evidence or tool-execution records made available during that
run.

## Tool Boundary

Each tool registration contains a stable identifier and version, effect, risk,
required scopes, Pydantic input and result types, and its executor. The registry is
explicit and rejects duplicate identifiers. Before execution, the runtime validates
arguments and checks Candidate scope, allowed effects, granted scopes, and maximum
risk. It records policy and execution outcomes, uses configurable iteration and
tool-call budgets, and stops on configured run or tool deadlines.

All production Candidate tools in the baseline are low-risk, read-only tools. The
general contracts can describe write-shaped tools, but no write tool is registered in
the Candidate investigation composition.

## Human and Policy Separation

**Human Approval is not Policy Authorization.**

A server-attributed human approval accepts one immutable proposal fingerprint. The
execution service then evaluates policy from persisted and server-owned facts
immediately before claiming execution. Approval cannot enable a disabled feature,
make an executor ready, change the allowlisted target, permit another action type, or
authorize a changed payload.

Human Candidate validation is also separate from action approval: validating a
Candidate creates registered TechnicalDebt but does not authorize an external write.

## Execution Boundary

External writes occur only through the `GitHubIssueExecutor` port after policy allows
the proposal. The GitHub Connector used for source acquisition is not that executor.
The execution service commits an in-progress claim, performs the network call outside
the database transaction, and persists a safe outcome.

Verification is a separate operation through `GitHubIssueVerifier`. It records
`PASS`, `FAIL`, or `UNAVAILABLE` and can reconcile a transport-uncertain execution
only when the external observation is unambiguous. An execution request or even a
`SUCCEEDED` execution is not a verified execution.

## PoC Security Boundary

The baseline fails closed for disabled or incomplete governance, provider, target,
executor, and verification configuration. Secrets use server-side settings, and CORS
requires explicit origins without a wildcard.

However, configured actor references and enablement flags are a local PoC seam, not
enterprise authentication, role-based authorization, or separation-of-duty
enforcement. The repository also does not implement production secrets management,
centralized audit export, deployment hardening, or operational monitoring. Live
OpenAI and GitHub behavior is opt-in; automated tests normally use controlled inputs
and bounded fakes.

## Related Documentation

- [System Architecture](system-architecture.md)
- [Extension Architecture](extension-architecture.md)
- [Architecture Decisions](architecture-decisions.md)
- [Implementation Status](../01-overview/implementation-status.md)

