# Architecture baseline

Baseline: 5 September 2026, Day 2 / Package 5 complete. **CURRENT** describes
repository code; **TARGET** describes future Option B work. [ADR 0001](../adr/0001-option-b-extensible-modular-monolith.md)
records the decision; [domain invariants](../domain/invariants.md) govern both
views. Connector extension is documented in
[adding a connector](../extensions/adding-a-connector.md). Database evolution is
documented in
[evolution and migrations](../database/evolution-and-migrations.md).

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
| Delivery | `backend/app/main.py`, `backend/app/api/v1`, Nuxt `frontend/app/pages/candidates`, and Nuxt `frontend/app/pages/sources` |

The development population command in `backend/app/development_population.py`
uses a fixed Semgrep + seeded-incident slice; it is not the entire ingestion
inventory. Evaluation ground truth remains separate from runtime data.

### Current dependency reality

The domain imports no persistence code. Source acquisition adapters do not
depend on API/UI. Source-specific ingestion functions call concrete adapters
and construct canonical objects.

```text
API → infrastructure Candidate read model → persistence + domain/context
API response mapping → infrastructure read-model DTOs + domain
Source ingestion → concrete source adapters + canonical domain objects
```

The API delegates SQL work but calls the infrastructure read model directly.
Consequently, this is **not yet full Ports & Adapters**. That dependency is a
known, non-blocking gap, not an implied application port.

There is currently no Agent Tool Contract, Tool Registry, Policy Port, Knowledge
provider contract, TechnicalDebt lifecycle implementation, or agent runtime.
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

Signal, Evidence, Candidate, canonical enterprise context, deterministic
correlation, and governance semantics form the stable conceptual core. The
future TechnicalDebt lifecycle also belongs here once implemented. This is a
semantic boundary: correlation currently lives in `backend/app/candidate_correlation.py`,
not in a newly introduced core package.

The core owns source-independent meaning and invariants. Scanner payloads,
provider SDKs, SQLAlchemy models, HTTP schemas, UI state, execution mechanics,
and registry wiring belong outside it. Governance principles already constrain
the project; executable approval/policy/lifecycle machinery is future work.

### Target extension surfaces

| Surface | Current status / intended responsibility |
| --- | --- |
| Connector Contract | Implemented for dependency-lifecycle and github-issues: acquire observations/findings with provenance. GitHub Issues stop at SourceObservation |
| Normalizer Contract | Implemented as a functional dependency-lifecycle boundary mapping to canonical `NormalizedSignal` / Signal + Evidence |
| Connector Registry | Implemented as deterministic, explicit in-code composition outside the domain |
| Agent Tool Contract | Describe bounded capabilities and their inputs/results |
| Tool Registry | Discover/compose tools; availability does not grant permission |
| Policy Port | Check whether proposed execution is permitted |
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
closure. This sequence describes future responsibilities, not current agents,
tools, policy enforcement, or audit persistence capabilities.

## CURRENT database / migration inventory

The handover-ready schema, ERD, migration coverage, and evolution guidance live
in [evolution and migrations](../database/evolution-and-migrations.md). Day 2
Packages 2–4 made **NO SCHEMA CHANGE**.

MSSQL is accessed using synchronous SQLAlchemy 2 with `mssql+pyodbc`; Alembic
owns schema versioning. Migrations are in `backend/alembic/versions`, configured
by `backend/alembic.ini` and `backend/alembic/env.py`.

Repository revision chain:

```text
20260826_01 → 20260827_01 → 20260828_01 → 20260831_01
```

The single repository head is **20260831_01**. This inventory does not assert
the applied revision of any live database.

| Revision | Schema responsibility |
| --- | --- |
| `20260826_01` | Initial revision baseline; no application tables |
| `20260827_01` | `enterprise_assets`, `teams`, `asset_ownerships`, `asset_relationships`, `incidents` |
| `20260828_01` | `signals`, `evidence` |
| `20260831_01` | `candidates`, `candidate_signals` |

Signal references its affected enterprise asset; Evidence references Signal.
Candidate links to Signals through `candidate_signals` and references its
canonical enterprise asset. Ownerships, relationships, and incidents enrich
enterprise context; these facts are not validation or causal conclusions.
**No TechnicalDebt table exists. NO schema change was made in this package.**
Alembic `env.py` now imports enterprise, signal, and candidate ORM models, so
target metadata includes `candidates` and `candidate_signals`. That metadata
completeness was corrected during the 4 September re-baseline; it required
NO schema change and NO migration revision.

## CURRENT frontend baseline

Nuxt 4 / Vue / TypeScript provides `/candidates`, `/candidates/[id]`, and
`/sources`; `frontend/app/pages/index.vue` redirects `/` to `/candidates`.
Candidate pages use `useCandidateApi` and real FastAPI Candidate GET endpoints.
Sources & Connectors uses `useConnectorApi` and real `GET /api/v1/connectors`.
There is no runtime mock fallback. Blank `runtimeConfig.public.apiBaseUrl`
raises a configuration error; pages show failure rather than silently
substituting mock data. Configure `NUXT_PUBLIC_API_BASE_URL` as the API origin.
Pool search and asset-type filtering are client-side.

`frontend/app/components/navigation/AppNavigation.vue` contains **Candidates**
and **Sources & Connectors**. The Sources page is registry inventory, not a
health dashboard: Registered is not Healthy, Connected, or Online. Future
information architecture may still grow toward Technical Debt and
Audit / Assurance. Those workspaces are not implemented.

## Known non-blocking gaps — intentionally deferred

| Verified gap | Deferred treatment |
| --- | --- |
| Candidate API calls `infrastructure/database/candidate_read_model.py` directly | Introduce an application read boundary in a later read-path slice |
| `api/v1/candidate_schemas.py` maps infrastructure `CandidateSummary` / `CandidateDetail` DTOs | Revisit DTO ownership with that read boundary |
| Correlation has an `incident-management` / `OPERATIONAL_INCIDENT` recurrence branch requiring at least two distinct Signals | Revisit source-independent problem-family semantics in a correlation slice; preserve current behavior now |

These remaining gaps are intentionally deferred beyond this connector package.
