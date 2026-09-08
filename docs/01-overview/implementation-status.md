# Implementation Status

This document describes the Current PoC Baseline based on the repository
implementation and automated tests.

Status values mean:

- **Implemented:** present in application code and exercised by automated tests.
- **Controlled PoC:** implemented behind controlled data, configuration, or an
  opt-in external dependency.
- **Partial:** a useful subset exists, but the wider lifecycle or integration does not.
- **Future / Production Requirement:** intentionally outside the current PoC baseline.

## Capability Status

| Area | Capability | Status | Notes |
|---|---|---|---|
| Data sources | Semgrep | Implemented | Three local Python rules map hard-coded endpoints, missing timeouts, and process-local state to canonical signal types. |
| Data sources | Git / SATD | Implemented | PyDriller-based scanning detects newly added self-admitted technical-debt comments and preserves commit, path, line, and timestamp. |
| Data sources | Incident ingestion | Controlled PoC | Seeded incidents are normalized to `OPERATIONAL_INCIDENT` Signals. The development population uses the synthetic estate. |
| Data sources | Dependency lifecycle / EOL | Controlled PoC | A registered local-JSON Connector, validated loader, normalizer, and persistence path support `DEPENDENCY_EOL` Signals. |
| Data sources | GitHub Issues read integration | Controlled PoC | A registered read-only HTTPS Connector fetches configured Issues. It is tested separately and has no Signal normalizer in the current baseline. |
| Signal processing | Canonical normalization | Implemented | Supported sources produce `NormalizedSignal` objects containing a Signal and matching non-empty Evidence set. |
| Signal processing | Duplicate handling | Implemented | Stable source-derived identities and persistence constraints make repeated ingestion duplicate-safe. |
| Signal processing | Evidence and provenance | Implemented | Source references, timestamps, optional URIs, source system, and source-record identity are persisted and returned by Candidate reads. |
| Candidate processing | Deterministic correlation | Implemented | Grouping uses canonical asset and exact problem family. Recurring incidents require at least two distinct incident Signals on one asset. |
| Enterprise context | Assets, ownership, and relationships | Controlled PoC | SQL-backed read models use the synthetic application, service, repository, team, ownership, and relationship estate. |
| Enterprise context | Incident context | Controlled PoC | Direct incidents for the Candidate asset are included in enterprise-context reads. |
| Enterprise context | Dependency reachability | Implemented | A directed service graph reports anchors, direct dependencies, direct dependents, and reachable dependents without inferring impact. |
| Agent | Investigation runtime | Implemented | Runs are bounded, audited, and end in supported assessment, abstention, or failure. |
| Agent | Registered read tools | Implemented | Exactly three tools read Candidate Evidence, dependency context, and enterprise context. |
| Agent | Structured assessment | Implemented | Outcomes, grounded claims, Evidence/tool references, missing evidence, uncertainties, recommendation, and stop reason are typed. |
| Agent | Provider boundary | Implemented | The runtime depends on an `InvestigationProvider` port rather than a concrete model provider. |
| Agent | Deterministic provider | Implemented | This is the default provider and exercises the three persisted read paths without live model inference. |
| Agent | OpenAI provider | Controlled PoC | An opt-in Responses API adapter uses structured output and controlled tool calls; its live smoke test requires explicit paid-test configuration. |
| Agent | Tool policy and trace | Implemented | Schema validation, candidate scope, effect, risk, scopes, hashed safe input summary, timing, result references, and policy outcome are recorded. |
| Agent | Runtime limits and stop conditions | Implemented | Iteration, tool-call, run-time, and tool-time limits are configured; safe stop reasons cover evidence, policy, budget, tool, provider, and internal failures. |
| Governance | Human validation | Controlled PoC | Configuration-gated API supports `VALIDATE`, `REJECT`, and `REQUEST_INFO`, legal transitions, expected revision, and server-owned actor identity. |
| Governance | TechnicalDebt creation | Implemented | `VALIDATE` atomically creates a TechnicalDebt linked to its Candidate and creating HumanDecision. |
| Governance | TechnicalDebt lifecycle | Partial | `REGISTERED` is the only implemented lifecycle state; verification does not close a record. |
| Governance | Action proposal | Implemented | The server prepares an immutable `CREATE_GITHUB_ISSUE` preview, marker, target, and canonical payload fingerprint without an external write. |
| Governance | Human action approval | Controlled PoC | A server-authorized actor approves the exact stored fingerprint; stale and competing approvals are rejected. |
| Governance | Execution policy | Implemented | Policy checks feature state, executor readiness, action type, allowlisted repository, approval presence, and fingerprint equality in fixed order. |
| Governance | Audit state | Implemented | Human decisions and all proposal, approval, action-policy, execution, and verification records are persisted and exposed in read models. |
| External execution | GitHub Issue executor | Controlled PoC | A separate executor can create one configured Issue when enabled and supplied a server-side token. Writes are disabled by default. |
| External execution | Claim and outcome handling | Implemented | The execution claim is stored before the network call; outcomes distinguish success, definite failure, and transport uncertainty, with duplicate/competing execution guards. |
| External execution | Verification and reconciliation | Controlled PoC | A separate GET-only verifier checks reference, marker, title, and fingerprint and can reconcile one unambiguous match after an uncertain outcome. |
| Persistence | Microsoft SQL Server | Controlled PoC | `pyodbc` and SQLAlchemy support the configured system of record; database integration tests require `DATABASE_URL`. |
| Persistence | SQLAlchemy mappings | Implemented | Models and repositories cover estate, Signals/Evidence, Candidates, agent audit, human decisions, TechnicalDebt, and governed actions. |
| Persistence | Alembic migrations | Implemented | Versioned migrations create and evolve the current schema through action verification. |
| Persistence | Seed and population commands | Controlled PoC | Idempotent estate seeding and an explicitly enabled development population provide reproducible controlled data. |
| Frontend | Overview and source inventory | Implemented | Nuxt pages summarize the Candidate collection and display registered Connector metadata. Registration is not shown as health or ingestion success. |
| Frontend | Candidate list and detail | Implemented | Users can filter Candidates and inspect Signals, Evidence, provenance, enterprise context, dependency context, and governance state. |
| Frontend | Agent investigation | Implemented | The Candidate detail can start and display a run, structured assessment, references, tool trace, and policy trace. |
| Frontend | Human validation | Implemented | The Candidate detail presents valid actions and submits validation with the current governance revision. Backend configuration still controls authority. |
| Frontend | TechnicalDebt portfolio and detail | Implemented | Pages show registered records, source Candidate, creating decision, and persisted action history. |
| Frontend | Governed action workbench | Implemented | The UI supports preview preparation, exact-payload approval, execution, verification, external reference display, and audit presentation. Backend policy remains authoritative. |
| Testing | Backend automated coverage | Implemented | Unit and API tests cover domain invariants, normalization, correlation, agent runtime/tools/providers, governance, action policy/execution/verification, connectors, and persistence behavior. |
| Testing | Database integration coverage | Controlled PoC | Opt-in tests exercise migrations and Microsoft SQL Server persistence when infrastructure is configured. |
| Testing | External integration coverage | Controlled PoC | GitHub read and OpenAI live tests are opt-in; executor and verifier behavior otherwise use bounded fakes in automated tests. |
| Testing | Frontend automated coverage | Implemented | Vitest tests cover API adapters, mapping, view-state logic, navigation, validation, investigation, and action-workbench behavior. |

## Current PoC Boundary

The demonstration estate and operational context are synthetic. Controlled repositories
contain intentional Semgrep findings; incidents and ownership are seeded; dependency
lifecycle observations come from a controlled JSON source. These fixtures make the
system reproducible without production institutional data.

GitHub provides the reference read and governed-write integration. Live reads,
execution, and verification require explicit repository and credential configuration.
The OpenAI provider is similarly optional; the deterministic provider is the default.

The API and UI implement the governance workflow, but server settings stand in for a
production identity and authorization system. Source acquisition is not a general
scheduler, and the registered GitHub Issues Connector is not yet a Signal ingestion
pipeline.

## Not Yet Production-Ready

The following are production requirements rather than defects in the current PoC:

- enterprise identity, role-based access control, and separation-of-duty integration;
- real CMDB, incident-management, dependency-intelligence, and broader repository or
  work-management sources;
- managed secrets, deployment infrastructure, security hardening, and environment
  governance;
- production observability, centralized audit export, alerting, and operational
  ownership;
- scale, resilience, scheduling, back-pressure, and recovery design based on measured
  workloads; and
- a broader TechnicalDebt lifecycle beyond registration.

See [Production Readiness](../07-handover-and-roadmap/production-readiness.md) for the
detailed production boundary.

## Related Documentation

- [System Overview](system-overview.md)
- [System Architecture](../02-architecture/system-architecture.md)
- [Production Readiness](../07-handover-and-roadmap/production-readiness.md)
