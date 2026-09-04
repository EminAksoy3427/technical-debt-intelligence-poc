# Architecture baseline

Baseline: 4 September 2026, Day 1 / Package 2. This is a documentation-only
re-baseline. **CURRENT** describes repository code; **TARGET** describes future
Option B work. [ADR 0001](../adr/0001-option-b-extensible-modular-monolith.md)
records the decision; [domain invariants](../domain/invariants.md) govern both views.

## CURRENT: layered modular monolith

```text
Sources
  → source adapters
  → source-specific normalizers
  → NormalizedSignal (Signal + Evidence)
  → deterministic Candidate correlation
  → persistence / read model
  → FastAPI
  → Nuxt Candidate Pool / Detail
```

This is a logical data flow, not an HTTP ingestion pipeline. Candidate GETs read
persisted data; they do not scan sources or trigger correlation.

| Responsibility | Current implementation |
| --- | --- |
| Acquisition | Semgrep and Git SATD scanners, dependency lifecycle JSON loader in `backend/app/infrastructure`; persisted incident loading under `infrastructure/database` |
| Normalization | `semgrep_ingestion.py`, `git_history_ingestion.py`, `dependency_lifecycle_ingestion.py`, `incident_ingestion.py` under `backend/app` |
| Canonical output | `backend/app/signal_ingestion.py`: `NormalizedSignal` bundles a Signal with matching, nonempty Evidence |
| Correlation | `backend/app/candidate_correlation.py`: canonical asset and problem-family grouping, deterministic identifiers and rationale |
| Persistence / context | `backend/app/infrastructure/database`: SQLAlchemy models, persistence, enterprise/dependency context and Candidate read model |
| Delivery | `backend/app/main.py`, `backend/app/api/v1`, and Nuxt `frontend/app/pages/candidates` |

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

There is currently no explicit Connector Contract, Normalizer Contract,
Connector Registry, Agent Tool Contract, Tool Registry, Policy Port, Knowledge
provider contract, TechnicalDebt lifecycle implementation, or agent runtime.
Existing functions and `NormalizedSignal` provide useful seams for future
contract extraction; they do not constitute those extension contracts today.

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

| Surface (not implemented as an explicit contract today) | Intended responsibility |
| --- | --- |
| Connector Contract | Acquire observations/findings with provenance |
| Normalizer Contract | Map findings to canonical `NormalizedSignal` / Signal + Evidence |
| Connector Registry | Select and compose connectors outside the domain |
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

### 5 September connector direction — TARGET only

The future Connector Contract should live outside pure domain and represent
acquisition of source observations/findings. It must preserve provenance and
feed a Normalizer Contract whose output is canonical `NormalizedSignal`
(Signal + Evidence). Acquisition must not know Candidate correlation or the
frontend, perform lifecycle validation, or authorize actions. Keep registry
wiring simple; a runtime plugin framework is not a prerequisite.

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

Nuxt 4 / Vue / TypeScript provides `/candidates` and `/candidates/[id]`;
`frontend/app/pages/index.vue` redirects `/` to `/candidates`.
Both pages use `useCandidateApi` and real FastAPI Candidate GET endpoints.
There is no runtime mock fallback. Blank `runtimeConfig.public.apiBaseUrl`
raises `CandidateApiConfigurationError`; pages show failure rather than silently
substituting mock data. Configure `NUXT_PUBLIC_API_BASE_URL` as the API origin.
Pool search and asset-type filtering are client-side.

`frontend/app/components/navigation/AppNavigation.vue` contains **Candidates
only**. Future information architecture may grow toward Candidates, Technical
Debt, Sources & Connectors, and Audit / Assurance. This is **TARGET direction
only**; no placeholder pages or navigation entries are added here.

## Known non-blocking gaps — intentionally deferred

| Verified gap | Deferred treatment |
| --- | --- |
| Candidate API calls `infrastructure/database/candidate_read_model.py` directly | Introduce an application read boundary in a later read-path slice |
| `api/v1/candidate_schemas.py` maps infrastructure `CandidateSummary` / `CandidateDetail` DTOs | Revisit DTO ownership with that read boundary |
| Correlation has an `incident-management` / `OPERATIONAL_INCIDENT` recurrence branch requiring at least two distinct Signals | Revisit source-independent problem-family semantics in a correlation slice; preserve current behavior now |
| Explicit connector/normalizer/registry contracts do not exist | Extract minimal contracts with the planned connector vertical slice |

None of these remaining gaps is fixed by this documentation package.
