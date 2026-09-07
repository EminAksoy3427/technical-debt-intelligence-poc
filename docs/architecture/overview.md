# Architecture baseline

Baseline: 6 September 2026, Day 4 / Package 6 complete. **CURRENT** describes
repository code; **TARGET** describes future Option B work. [ADR 0001](../adr/0001-option-b-extensible-modular-monolith.md)
records the decision; [domain invariants](../domain/invariants.md) govern both
views. Connector extension is documented in
[adding a connector](../extensions/adding-a-connector.md). Database evolution is
documented in
[evolution and migrations](../database/evolution-and-migrations.md).
Day 4 acceptance is recorded in
[the Day 4 checkpoint](../checkpoints/day-4-human-validation-technical-debt.md).

## CURRENT: layered modular monolith

```text
Sources
  → source acquisition (explicit Connector for dependency-lifecycle and github-issues)
  → SourceObservation (dependency-lifecycle, github-issues)
  → source-specific normalizers (dependency-lifecycle only; github-issues not yet)
  → NormalizedSignal (Signal + Evidence)
  → deterministic Candidate correlation
  → persistence / read model
  → FastAPI
  → Nuxt Candidate Pool / Detail
```

Human Validation is a separate command plane. It does not run behind
AgentRuntime:

```text
READ / investigation plane
  Nuxt Agent Investigation
    → FastAPI AgentRun POST/GET
    → AgentRuntime → Tool Registry → Policy → Candidate READ tools
    → MSSQL audit persistence

Human governance command plane
  Nuxt Human Validation / Technical Debts
    → FastAPI
    → apply_human_validation
    → domain / persistence
    → MSSQL
```

This remains one **Extensible Modular Monolith**. It is not microservices.

Connector Registry visibility is a separate read path. It does not acquire
source records:

```text
Connector Registry
  → descriptor metadata only
  → FastAPI GET /api/v1/connectors
  → Nuxt Sources & Connectors
```

The first diagram is a logical data flow, not an HTTP ingestion pipeline.
Candidate GETs read persisted data; they do not scan sources or trigger
correlation. Connector GETs read registry descriptors; they do not execute
connectors.

| Responsibility | Current implementation |
| --- | --- |
| Acquisition | Dependency lifecycle and GitHub Issues use the explicit connector seam in `backend/app/connectors`; Semgrep and Git SATD scanners remain in `backend/app/infrastructure`; persisted incident loading remains under `infrastructure/database` |
| Normalization | `semgrep_ingestion.py`, `git_history_ingestion.py`, `dependency_lifecycle_ingestion.py`, `incident_ingestion.py` under `backend/app` |
| Canonical output | `backend/app/signal_ingestion.py`: `NormalizedSignal` bundles a Signal with matching, nonempty Evidence |
| Correlation | `backend/app/candidate_correlation.py`: canonical asset and problem-family grouping, deterministic identifiers and rationale |
| Persistence / context | `backend/app/infrastructure/database`: SQLAlchemy models, persistence, enterprise/dependency context and Candidate read model |
| Human Validation | `backend/app/governance`: contracts, transitions, and `apply_human_validation`; persistence under `infrastructure/database` |
| Delivery | `backend/app/main.py`, `backend/app/api/v1`, Nuxt `frontend/app/pages/overview`, `frontend/app/pages/candidates`, `frontend/app/pages/technical-debts`, and `frontend/app/pages/sources` |

The development population command in `backend/app/development_population.py`
uses a fixed Semgrep + seeded-incident slice; it is not the entire ingestion
inventory. Evaluation ground truth remains separate from runtime data.

### Current dependency reality

The domain imports no persistence code. Source acquisition adapters do not
depend on API/UI. Source-specific ingestion functions call concrete adapters
and construct canonical objects.

```text
API → infrastructure Candidate / TechnicalDebt read models → persistence + domain/context
API Human Validation → apply_human_validation → persistence helpers (flush only)
API response mapping → infrastructure read-model DTOs + domain
Source ingestion → concrete source adapters + canonical domain objects
```

The API delegates SQL work but calls the infrastructure read model directly.
Consequently, this is **not yet full Ports & Adapters**. That dependency is a
known, non-blocking gap, not an implied application port.

An explicit typed Agent Tool contract, deterministic Tool Registry, and
deterministic Policy boundary exist for Candidate-scoped READ tools:
`read_candidate_evidence`, `read_candidate_dependency_context`, and
`read_candidate_enterprise_context`. Typed Structured Assessment, AgentRun,
ToolExecution, and PolicyDecision audit contracts and persistence now exist as
the audit boundary for a synchronous bounded Agent Runtime. The runtime uses an
explicit provider decision port, deterministic providers, and an optional live
OpenAI adapter. It enforces
iteration/tool/time budgets, evaluates registry-owned metadata through the
deterministic Policy boundary before execution, and checkpoints audit records.
There is currently no Knowledge provider contract or production WRITE tool.
Human Validation is a FastAPI command served by `apply_human_validation`, not
an Agent Tool. TechnicalDebt exists only as a REGISTERED provenance record
created by a valid Human `VALIDATE`. Candidate Detail includes separate Agent
Investigation and Human Validation sections.

```text
Candidate → AgentRun → provider decision → Tool Registry → Policy
          → Candidate READ tool → durable audit → Structured Assessment
```

The bounded runtime is exposed only through Candidate-scoped POST/GET AgentRun
routes. POST accepts no prompt, tool, authorization, provider, or model
configuration. Server composition selects the default deterministic provider or
the optional OpenAI Responses API adapter from trusted settings, and supplies the
existing READ/LOW-risk authorization. GET loads a persisted
aggregate scoped by both Candidate and AgentRun identity and exposes only safe
product/audit response models. Runtime checkpoint commits are not enclosed in
an API-wide transaction, so terminal FAILED and ABSTAINED resources remain
durable. Those AgentRun checkpoint semantics are not the Human Validation
transaction. Candidate Detail renders a persisted AgentRun through the Agent
Investigation section. The client cannot select or discover the provider/model.

### CURRENT Human Validation transaction

`apply_human_validation` requires a transaction-free Session. The service owns:

```text
BEGIN → Candidate row lock → read history → validate command → write → COMMIT / ROLLBACK
```

Persistence helpers flush but do not commit. Same-Candidate commands are
serialized on MSSQL with `UPDLOCK` and `HOLDLOCK` on the Candidate row, plus
database uniqueness on `(candidate_id, sequence_number)`,
`source_candidate_id`, and `creation_human_decision_id`. Actor identity is
server-owned from `HUMAN_GOVERNANCE_ENABLED` and
`HUMAN_GOVERNANCE_ACTOR_REFERENCE`. That seam is not enterprise
authentication.

Initial Candidate governance is `PENDING` at revision 0. Legal Day 4
transitions:

```text
PENDING
  VALIDATE     → VALIDATED
  REJECT       → REJECTED
  REQUEST_INFO → INFORMATION_REQUESTED

INFORMATION_REQUESTED
  VALIDATE     → VALIDATED
  REJECT       → REJECTED
  REQUEST_INFO → INFORMATION_REQUESTED
```

`VALIDATED` and `REJECTED` are terminal for Day 4. `MERGE` is deferred.
VALIDATE persists one HumanDecision and exactly one REGISTERED TechnicalDebt
atomically. REJECT and REQUEST_INFO persist a HumanDecision and create no
TechnicalDebt. Duplicate or stale commands conflict; there is no silent
idempotency.

Provider-visible context contains bounded registry-derived tool descriptors,
typed input schemas, and validated tool results, not sessions, settings,
credentials, authorization authority, hidden reasoning, or evaluation ground
truth. The live adapter uses a real HTTP request timeout no greater than the
overall run budget and disables SDK retries. Synchronous tool timeout handling
still accounts for elapsed deadlines after a tool returns; it does not claim
hard cancellation of arbitrary Python calls.
The dependency-lifecycle vertical slice implements an explicit Connector,
SourceObservation, functional normalizer boundary, and Connector Registry
contracts. GitHub Issues is registered as a second explicit connector and
stops at SourceObservation. The Connector Registry is visible through
`GET /api/v1/connectors` and the Nuxt Sources & Connectors page as inventory
metadata only: `status=registered` means composition registration, not source
health. The other acquisition paths remain legacy-compatible.

### CURRENT connector acquisition seam

```text
External/local source
  → Connector
  → SourceObservation
  → Normalizer
  → NormalizedSignal
  → persistence / correlation
```

The Connector collects source-specific records and attaches their existing
provenance and observation time. The Normalizer maps an observation through the
existing canonical normalization function; required asset resolution remains an
explicit caller dependency. The Registry composes registrations explicitly in
code, with deterministic order and duplicate identifier rejection.

Registered reference connectors:

1. `dependency-lifecycle` — transport: local JSON
2. `github-issues` — transport: HTTPS, READ-only

Dependency-lifecycle acquisition flow:

```text
local JSON
  → Connector
  → SourceObservation
  → Normalizer
  → NormalizedSignal
```

GitHub Issues flow:

```text
GitHub REST API
  → Connector
  → SourceObservation
```

GitHub Issues are not yet normalized into a canonical Signal. GitHub Issues
are not Candidates. GitHub Issues are not TechnicalDebt. The GitHub connector
is acquisition-only. Pagination, polling, and checkpoints are not implemented;
the current GET reads a single first page of open issues, which is sufficient
for the public two-issue demo source.

`dependency-lifecycle` remains the only registered source with a canonical
normalizer. Semgrep, Git SATD, and Incident ingestion are not yet migrated.
Connectors and the Registry have no Candidate or TechnicalDebt knowledge, and
this seam is not a dynamic plugin system: it performs no runtime discovery,
scanning, entry-point loading, or marketplace orchestration. See
[adding a connector](../extensions/adding-a-connector.md) for the current
extension workflow.

## TARGET: Option B

**Extensible Modular Monolith + Ports & Adapters + Explicit Extension Contracts +
Governed Agent Runtime + Async-ready seams + MSSQL/Alembic System of Record.**

This is an incremental direction, not a description of completed implementation.
Async-ready seams mean boundaries that can later support asynchronous execution;
they do not imply a queue or distributed deployment exists.

Intended code dependency direction (arrows mean “depends on”):

```text
Delivery / API
    ↓
Application / orchestration → application-owned ports (outside pure domain)
    ↓                                     ↑
Stable Core                     infrastructure adapters implement ports
```

The core must not depend on concrete adapters. Composition wires implementations
to ports. The current `API → infrastructure read model` path remains until a
separate vertical slice introduces an application read boundary.

### Stable Core boundary

Signal, Evidence, Candidate, HumanDecision, REGISTERED TechnicalDebt, canonical
enterprise context, deterministic correlation, and governance semantics form
the stable conceptual core. Remaining TechnicalDebt lifecycle beyond
REGISTERED still belongs here once implemented. This is a
semantic boundary: correlation currently lives in `backend/app/candidate_correlation.py`,
not in a newly introduced core package.

The core owns source-independent meaning and invariants. Scanner payloads,
provider SDKs, SQLAlchemy models, HTTP schemas, UI state, execution mechanics,
and registry wiring belong outside it. Governance principles already constrain
the project; L3 ActionProposal and L4 approval/execution remain future work.

### Target extension surfaces

| Surface | Current status / intended responsibility |
| --- | --- |
| Connector Contract | Implemented for dependency-lifecycle and github-issues: acquire observations/findings with provenance. GitHub Issues stop at SourceObservation |
| Normalizer Contract | Implemented as a functional dependency-lifecycle boundary mapping to canonical `NormalizedSignal` / Signal + Evidence |
| Connector Registry | Implemented as deterministic, explicit in-code composition outside the domain |
| Agent Tool Contract | Implemented for Candidate-scoped READ tools with a bounded synchronous runtime, Candidate-scoped POST/GET AgentRun API, Candidate Detail Agent Investigation UI, and optional live OpenAI provider. Production WRITE tools are not implemented. Human Validation is not an Agent Tool |
| Tool Registry | Implemented as deterministic, explicit in-code composition. Availability does not grant permission |
| Policy Port | Implemented as a deterministic in-process Policy boundary. The runtime persists its decisions; persistence grants no authorization |
| Investigation provider | Typed next-step port, deterministic providers, and a stateless OpenAI Responses API adapter implemented. Provider selection is server-owned and deterministic remains the default |
| Knowledge capability/provider | Supply contextual knowledge through a replaceable boundary |

Introduce agent/tool/policy contracts only with their implemented vertical
slices. A registry is a composition/infrastructure concern, not domain logic.

Boundary examples:

- Good: retain `source_system` as provenance/evidence identity.
- Bad: add Semgrep-specific rule structures as Candidate domain fields.
- Good: a connector feeds a normalizer that produces canonical Signal/Evidence.
- Bad: the frontend calls Semgrep or Git scanner implementations directly.

### L4 governed execution — TARGET / FUTURE, not implemented

```text
Agent prepares → Human approves → Policy checks → Executor executes
               → Result verified → Audit persisted
```

AI proposes. Evidence explains. Human decides. Agent assessment is not
authorization, tool availability is not permission, and verification is not
closure. This sequence describes future L4 runtime, approval, and audit
persistence responsibilities. It does not describe the current Candidate READ
tools, Tool Registry, or in-process Policy boundary.

## CURRENT database / migration inventory

The handover-ready schema, ERD, migration coverage, and evolution guidance live
in [evolution and migrations](../database/evolution-and-migrations.md). Day 2
Packages 2–4 made **NO SCHEMA CHANGE**.

MSSQL is accessed using synchronous SQLAlchemy 2 with `mssql+pyodbc`; Alembic
owns schema versioning. Migrations are in `backend/alembic/versions`, configured
by `backend/alembic.ini` and `backend/alembic/env.py`.

Repository revision chain:

```text
20260826_01 → 20260827_01 → 20260828_01 → 20260831_01 → 20260905_01 → 20260906_01
```

The single repository head is **20260906_01**. This inventory does not assert
the applied revision of any live database.

| Revision | Schema responsibility |
| --- | --- |
| `20260826_01` | Initial revision baseline; no application tables |
| `20260827_01` | `enterprise_assets`, `teams`, `asset_ownerships`, `asset_relationships`, `incidents` |
| `20260828_01` | `signals`, `evidence` |
| `20260831_01` | `candidates`, `candidate_signals` |
| `20260905_01` | `agent_runs`, `tool_executions`, `policy_decisions` |
| `20260906_01` | `human_decisions`, `technical_debts` |

Signal references its affected enterprise asset; Evidence references Signal.
Candidate links to Signals through `candidate_signals` and references its
canonical enterprise asset. Ownerships, relationships, and incidents enrich
enterprise context; these facts are not validation or causal conclusions.
Candidates have no status or revision columns. HumanDecision history is
append-only; governance state and revision are derived from that history.
TechnicalDebt is a REGISTERED provenance row created only by a valid Human
`VALIDATE`. Agent audit persistence records bounded run state, grounded
assessment JSON, safe tool traces, and policy facts. The bounded runtime writes
those records but cannot validate a Candidate, create TechnicalDebt, or
authorize action.

## CURRENT frontend baseline

Nuxt 4 / Vue / TypeScript provides `/overview`, `/candidates`, `/candidates/[id]`,
`/technical-debts`, `/technical-debts/[id]`, and `/sources`.
`frontend/app/pages/index.vue` redirects `/` to `/overview`.
`/overview` is the product landing page. `/candidates` remains the Candidate
review queue.
Candidate pages use `useCandidateApi` and real FastAPI Candidate GET endpoints.
Candidate Detail sections are Overview, Evidence & Context, Agent
Investigation, and Human Validation. Agent Investigation and Human Validation
are visually and semantically separate.

Agent Investigation uses `useAgentRunApi` with the real AgentRun POST/GET API.
The investigation provider is server-selected; the UI sends no provider, model,
prompt, or authorization control and makes no claim about which provider ran.

Human Validation supports Validate, Reject, and Request information. The
frontend sends the current persisted governance revision. A 409 does not retry
the mutation; it refreshes the Candidate. If refresh after a successful POST
fails, the UI reports that the decision was saved but state could not be
refreshed and prevents duplicate submission. If conflict refresh fails, further
governance actions are disabled because the local revision may be stale.

TechnicalDebt portfolio and detail use `useTechnicalDebtApi`. They show
REGISTERED provenance and the source Candidate / creation VALIDATE decision.
They do not invent risk, effort, or owner.

Sources & Connectors uses `useConnectorApi` and real `GET /api/v1/connectors`.
There is no runtime mock fallback. Blank `runtimeConfig.public.apiBaseUrl`
raises a configuration error; pages show failure rather than silently
substituting mock data. Configure `NUXT_PUBLIC_API_BASE_URL` as the API origin.
Pool search and asset-type filtering are client-side.

`frontend/app/components/navigation/AppSidebar.vue` contains **Overview**,
**Candidates**, **Technical Debts**, and **Sources**. The Sources page is registry
inventory, not a health dashboard: Registered is not Healthy, Connected, or
Online. Future information architecture may still grow toward
Audit / Assurance. That workspace is not implemented.

## Known non-blocking gaps — intentionally deferred

| Verified gap | Deferred treatment |
| --- | --- |
| Candidate API calls `infrastructure/database/candidate_read_model.py` directly | Introduce an application read boundary in a later read-path slice |
| `api/v1/candidate_schemas.py` maps infrastructure `CandidateSummary` / `CandidateDetail` DTOs | Revisit DTO ownership with that read boundary |
| Correlation has an `incident-management` / `OPERATIONAL_INCIDENT` recurrence branch requiring at least two distinct Signals | Revisit source-independent problem-family semantics in a correlation slice; preserve current behavior now |

These remaining gaps are intentionally deferred beyond this connector package.
