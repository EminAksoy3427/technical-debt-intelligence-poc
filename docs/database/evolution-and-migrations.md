# Database evolution and migrations

Handover-ready notes for the current MSSQL / SQLAlchemy 2 / Alembic stack.
This is not an enterprise DBA manual.

Do not copy real credentials into this document. Safe placeholders only.

## Current technology

| Piece | Current choice |
| --- | --- |
| Database | MSSQL |
| ORM | SQLAlchemy 2, synchronous application database layer |
| Migrations | Alembic |
| Dialect | `mssql+pyodbc` |

FastAPI routers do not execute SQL directly. Persistence lives under
`backend/app/infrastructure/database`. Alembic configuration lives in
`backend/alembic.ini` and `backend/alembic/env.py`. Revisions live in
`backend/alembic/versions`.

`DATABASE_URL` is backend-only. It is not a Nuxt `runtimeConfig` value.

## Schema-as-code relationship

These artifacts are related but distinct:

| Artifact | Role |
| --- | --- |
| Domain models | canonical business meaning |
| SQLAlchemy ORM models | desired application mappings / metadata |
| Alembic revisions | migration history and DDL transitions |
| MSSQL runtime database + `alembic_version` | deployed state |
| Tests | verification evidence |

**ORM != Alembic != live DB.** They are not interchangeable. A model class,
a revision file, and a deployed database can drift. `alembic_version` records
the applied revision; it is Alembic bookkeeping, not an application-domain
table.

## Current schema inventory

Application tables:

- `enterprise_assets`
- `teams`
- `asset_ownerships`
- `asset_relationships`
- `incidents`
- `signals`
- `evidence`
- `candidates`
- `candidate_signals`
- `agent_runs`
- `tool_executions`
- `policy_decisions`

Also present at runtime after Alembic has run:

- `alembic_version` — Alembic bookkeeping only

There is **no** `technical_debt` table. There are **no** `connector`,
`connector_health`, `connector_run`, or `checkpoint` tables.

## DAY 2 PACKAGES 2–4: NO SCHEMA CHANGE

This was deliberate.

| Day 2 surface | Persistence |
| --- | --- |
| Connector contract | code only |
| GitHub connector | code/config only |
| Connector Registry API | code only |
| Sources & Connectors UI | frontend/API visibility only |

No connector persistence was added. Registry inventory remains in code.
Do not create connector tables merely because a connector exists.

## Current ERD

Relationships below are the current ORM relationships only. No invented
edges.

```mermaid
erDiagram
    enterprise_assets ||--o{ asset_ownerships : ownerships
    teams ||--o{ asset_ownerships : ownerships
    enterprise_assets ||--o{ asset_relationships : outgoing
    enterprise_assets ||--o{ asset_relationships : incoming
    enterprise_assets ||--o{ incidents : incidents
    enterprise_assets ||--o{ signals : affected
    enterprise_assets ||--o{ candidates : canonical
    signals ||--o{ evidence : evidence
    candidates ||--o{ candidate_signals : membership
    signals ||--o{ candidate_signals : membership
    candidates ||--o{ agent_runs : investigations
    agent_runs ||--o{ tool_executions : executions
    tool_executions ||--o| policy_decisions : decision

    enterprise_assets {
        int id PK
        string asset_key UK
        string asset_type
        string name
        string criticality
        string lifecycle_status
    }
    teams {
        int id PK
        string team_key UK
        string name
    }
    asset_ownerships {
        int id PK
        int asset_id FK
        int team_id FK
        string ownership_role
    }
    asset_relationships {
        int id PK
        int source_asset_id FK
        int target_asset_id FK
        string relationship_type
    }
    incidents {
        int id PK
        string incident_key UK
        int primary_affected_asset_id FK
        string severity
        string title
        datetime started_at
        datetime resolved_at
    }
    signals {
        uuid signal_id PK
        string source_system
        string source_record_id
        datetime detected_at
        string signal_type
        int affected_asset_id FK
        string severity
    }
    evidence {
        uuid evidence_id PK
        uuid signal_id FK
        string source_system
        string source_reference
        datetime captured_at
        string reference_uri
    }
    candidates {
        uuid candidate_id PK
        int canonical_asset_id FK
        string hypothesis
        string correlation_rationale
    }
    candidate_signals {
        uuid candidate_id PK, FK
        uuid signal_id PK, FK
    }
    agent_runs {
        uuid agent_run_id PK
        uuid candidate_id FK
        string status
        datetime created_at
        datetime started_at
        datetime completed_at
        json structured_assessment
        string stop_reason
    }
    tool_executions {
        uuid tool_execution_id PK
        uuid agent_run_id FK
        int sequence_number
        string tool_id
        string tool_version
        string input_hash
        json safe_input_summary
        string status
        int duration_ms
        json result_references
    }
    policy_decisions {
        uuid tool_execution_id PK, FK
        string decision
        string requested_effect
        string requested_risk
        json required_scopes
        json granted_scopes
        string maximum_risk
        string rule_id
        string reason_code
        datetime decided_at
    }
```

Notes that match the ORM:

- `asset_ownerships` joins `enterprise_assets` and `teams`.
- `asset_relationships` is a directed edge between two enterprise assets.
- `incidents` reference one primary affected asset.
- `signals` reference one affected enterprise asset.
- `evidence` belongs to a signal.
- `candidates` reference one canonical enterprise asset.
- `candidate_signals` is the Candidate–Signal membership table.
- Candidates do not own Evidence rows directly; Evidence remains on Signal.
- AgentRuns belong to a Candidate and store an optional validated Structured
  Assessment JSON document.
- ToolExecutions are ordered audit records within one AgentRun. Their input
  summary is limited to allowlisted Candidate identity and paired with a
  canonical SHA-256 hash; raw tool payloads are not stored.
- A ToolExecution has at most one PolicyDecision, keyed by the ToolExecution
  identifier. Policy facts record registry metadata and trusted authorization
  context without duplicating the AgentRun identifier.

## Migration history

Exact current chain, single head, no branching:

```text
20260826_01 → 20260827_01 → 20260828_01 → 20260831_01 → 20260905_01
```

Current head: **`20260905_01`**.

| Revision | Purpose |
| --- | --- |
| `20260826_01` | baseline, no schema change |
| `20260827_01` | enterprise estate foundation |
| `20260828_01` | signals + evidence |
| `20260831_01` | candidates + `candidate_signals` |
| `20260905_01` | AgentRun, ToolExecution, and PolicyDecision audit persistence |

This inventory describes repository revisions. It does not assert the applied
revision of any live database until that database is inspected.

## Schema vs data

| Mechanism | Role |
| --- | --- |
| Alembic revisions | schema migration |
| `seed_enterprise_estate` / `SYNTHETIC_*` | synthetic seed/reference estate |
| `development_population.py` | development/demo population |
| `synthetic_sources` | controlled source input |
| `synthetic_repositories` | controlled scanner input |
| `evaluation/ground_truth` | evaluation fixture only |

Ground truth must remain isolated from runtime behavior. Do not perform
production backfills via demo seed logic.

## Future data migrations

If a real production data migration or backfill becomes necessary, use an
explicit reviewed data-migration strategy. Possible forms:

- an Alembic data migration
- a dedicated reviewed one-off migration

Do **not** hide production data migration inside:

- `seed_enterprise_estate`
- `development_population`
- evaluation fixtures

## Compatibility: CURRENT vs FUTURE PRACTICE

**CURRENT**

- migrations create tables
- no expand/migrate/contract workflow exists
- no destructive column migrations exist

**FUTURE PRACTICE**

Prefer additive, backward-compatible evolution. For larger changes:

```text
expand → migrate → contract
```

That sequence is guidance only. It is not implemented as a current workflow.

## Rollback / roll-forward

Actual downgrade functions:

| Revision | Downgrade |
| --- | --- |
| `20260826_01` | no-op |
| later migrations | drop the tables they created |

This is useful for disposable/dev databases. It may be destructive when data
exists.

Guidance:

- **Development:** downgrade may be acceptable for disposable data.
- **Production-aware recovery:** prefer roll-forward for irreversible or
  data-bearing failures.

Do not always downgrade. Full production rollback automation does not exist.

## Migration verification coverage

Statuses below are honest against currently inspected evidence, including the
Package 3 migration compilation and configured-MSSQL integration run.

| Claim | Status | Evidence |
| --- | --- | --- |
| Single head | **PROVEN** | Alembic script directory; `20260905_01` is the only head |
| Clean DB → head | **PARTIALLY PROVEN** | live MSSQL upgrade-to-head exists; a guaranteed empty-database bootstrap is not a dedicated proven path |
| Existing DB → head | **PARTIALLY PROVEN** | the configured MSSQL database successfully ran `upgrade head` and exposed the new schema; its starting revision was not separately captured |
| Live downgrade | **NOT PROVEN** | downgrade SQL is compiled in-process (`as_sql`); no live MSSQL downgrade test was found |
| Upgrade after downgrade | **NOT PROVEN** | no round-trip test exists |
| ORM/schema correspondence | **PARTIALLY PROVEN** | ORM metadata, Alembic `env.py` imports, compiled MSSQL CREATE TABLE SQL, and live audit table/FK/index inspection are checked; complete live column/constraint parity is not proven |
| Actual MSSQL migration | **PROVEN for Package 3 audit persistence** | integration tests upgraded configured MSSQL to head, inspected audit tables/FKs/index, and round-tripped AgentRun, Structured Assessment, ToolExecution, and PolicyDecision data |

Do not improve these claims without adding or running new proof.

## Safe MSSQL configuration

Use placeholders only. Example:

```text
DATABASE_URL=mssql+pyodbc:///?odbc_connect=<url-encoded-odbc-connection-string>
```

`DATABASE_URL` is backend-only. Put real values in an untracked `.env` or
process environment. Commit `backend/.env.example` only.

SQL authentication examples in `.env.example` are placeholders (`username`,
`password`, local instance names). Do not copy a real `.env`.

Integration tests that need MSSQL are marked `integration` and are excluded
from the deterministic suite:

```text
python -m pytest -m "not integration and not external"
```
