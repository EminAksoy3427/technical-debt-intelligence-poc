# Extension Architecture

## Purpose

Extension boundaries keep the application dependent on stable contracts while
technology-specific acquisition, AI, persistence, and mutation implementations remain
contained. The Current PoC Baseline combines formal protocols, typed registrations,
and explicit composition functions; it is not a dynamic plug-in system.

## Extension Points

| Extension Point | Responsibility | Example Current Implementation |
|---|---|---|
| Connector | Acquire source records with stable metadata, provenance, time, and read-only status. | `Dependency Lifecycle` local-JSON and `GitHub Issues` HTTPS registrations in `backend/app/connectors/registry.py` |
| Normalizer | Deterministically map a supported source record to canonical Signal and Evidence values. | `normalize_semgrep_finding`, `normalize_git_satd_finding`, `normalize_incident`, and `normalize_dependency_lifecycle_finding` |
| Agent Tool | Expose a typed capability with effect, risk, scopes, input schema, result schema, and executor. | The three Candidate read registrations built in `backend/app/agent/composition.py` |
| AI Provider | Select the next bounded investigation step without coupling the runtime to a model SDK. | Default deterministic provider and opt-in OpenAI provider selected in `backend/app/agent/provider_composition.py` |
| Policy seam | Evaluate trusted facts before a tool or external action is executed. The policies are concrete deterministic functions, not registry-loaded plug-ins. | `evaluate_candidate_tool_policy` and `evaluate_action_execution_policy` |
| Executor | Perform one authorized external mutation through an application-owned protocol. | `GitHubIssueExecutor` with `HttpGitHubIssueExecutor` |
| Verifier | Read external state through a separate protocol and compare it with persisted proposal authority. | `GitHubIssueVerifier` with `HttpGitHubIssueVerifier` |
| Registry / composition | Assemble known implementations explicitly and reject ambiguous identifiers. | `CONNECTOR_REGISTRY`, `ToolRegistry`, `build_candidate_tool_registry`, and FastAPI dependencies in `backend/app/api/dependencies.py` |

Normalizers currently follow explicit source-specific functions rather than a shared
normalizer protocol or registry. Executors and verifiers have protocols, but their
current API composition is specifically for GitHub Issues.

## Read and Write Separation

```text
Connector -> reads external or controlled source information
Executor  -> performs a policy-authorized external mutation
```

The Connector descriptors currently declare read-only acquisition. The GitHub Issue
executor is a different action-plane type, uses a separate configuration path, and is
only reached after proposal, approval, and policy evaluation. A dedicated verifier
then performs GET-only read-back.

This separation keeps source inventory from implying mutation authority, permits
connectors to be tested without executing actions, makes write policy independently
testable, and leaves persisted records for the proposal, approval, policy decision,
execution, and verification stages.

## Registry and Composition

Connector registration is an immutable, in-code tuple in
`backend/app/connectors/registry.py`. Each registration combines a descriptor and an
acquisition callable; duplicate connector identifiers are rejected. Listing the
registry returns composition metadata and does not run an acquisition.

Candidate tools are created around a `CandidateInvestigationReader`, collected in a
`ToolRegistry`, and composed with `DatabaseCandidateInvestigationReader` in
`backend/app/infrastructure/database/candidate_tool_composition.py`. The runtime sees
only registered descriptors and validated tool results.

The provider is selected from validated server settings. FastAPI dependencies build
the selected investigation provider and the configured GitHub executor and verifier.
No client request chooses the model, token, external target, or implementation.

## Adding a New Integration

At an architectural level, a new read integration follows this sequence:

```text
External system
  -> source-specific loader or transport
  -> Connector contract implementation
  -> source-specific canonical mapping, when it feeds Signals
  -> explicit registry or composition update
  -> contract, mapping, boundary and integration tests
```

A new mutation integration requires a separate application-owned executor contract,
deterministic authorization policy, persistence and audit handling, and independent
verification. It must not gain write access by extending a read Connector.

## Architecture Benefit

The explicit seams reduce coupling to current sources and providers, allow bounded
fakes in tests, keep mutation authority narrow, and make replacement or incremental
integration possible without placing GitHub or OpenAI semantics in the domain model.

## Related Documentation

- [System Architecture](system-architecture.md)
- [Module Boundaries](module-boundaries.md)
- [Security and Trust Boundaries](security-and-trust-boundaries.md)
- [Core Concepts](../01-overview/core-concepts.md)

