# Migrations, Seeding and Data Model Extension

## Schema Evolution

Database schema changes must be versioned through Alembic migrations.

Code changes alone do not modify an existing database. A migration records the
required transition so different environments can move through the same ordered
schema history. A migration is therefore part of a persistence change, not an optional
follow-up to a SQLAlchemy model edit.

## Alembic in This Repository

Alembic configuration is in `backend/alembic.ini`. Revision files live in
`backend/alembic/versions/`, and `backend/alembic/env.py` imports all current mapping
modules and exposes `Base.metadata` for schema comparison. The current revision chain
ends at `20260907_04`, which adds action verification persistence.

From `backend/`, after installing the backend dependencies and configuring the target
database, upgrade to the latest schema with:

```powershell
alembic upgrade head
```

This is the same upgrade target used by the MSSQL integration tests through Alembic's
Python API. The FastAPI application does not run migrations at startup.

Database access is configured through `DATABASE_URL` in `backend/app/core/config.py`.
The engine rejects any dialect other than `mssql+pyodbc`, enables connection
pre-ping, and applies the configured connection timeout. `backend/.env.example` gives
two supported URL shapes:

- Windows integrated authentication through a URL-encoded ODBC connection string;
- SQL authentication with an `mssql+pyodbc` URL.

Both examples use Microsoft ODBC Driver 17 for SQL Server. The database itself, the
ODBC driver, and an existing empty or previously migrated database must be available;
the migration chain creates application tables, not the SQL Server database.

## Migration vs Seed

| Operation | Meaning | Current repository example |
|---|---|---|
| Migration | Changes database structure. | `backend/alembic/versions/20260828_01_normalized_signal_persistence.py` creates the `signals` and `evidence` tables, constraints, and foreign keys. |
| Seed | Inserts or reconciles controlled data within an existing schema. | `backend/app/infrastructure/database/enterprise_estate_seed.py` materializes the synthetic assets, teams, ownerships, relationships, and incidents. |

Running a migration does not insert the enterprise estate. Running the seed does not
create missing tables. Apply migrations before seeding.

## Controlled Enterprise Seed

The source dataset is defined in
`backend/app/domain/synthetic_enterprise_estate.py`. It contains a small fictional
estate: eight assets, three teams, nine ownership assignments, eight directed
relationships, and four incidents.

Run the seed from `backend/` with a configured `DATABASE_URL`:

```powershell
python -m app.infrastructure.database.enterprise_estate_seed
```

The seed is idempotent for its logical baseline. Assets, teams, and incidents are
located by their stable keys and their controlled attributes are reconciled;
ownerships and relationships are inserted only when the same logical link is absent.
MSSQL integration tests run the seed twice and verify an unchanged controlled
snapshot. The seed does not delete unrelated rows or create Signals, Candidates,
Human Decisions, or TechnicalDebt.

Deterministic controlled data gives scanners, context readers, and integration tests
the same asset identities and relationships on every run without using production
institutional data.

### Development Candidate Population

`backend/app/development_population.py` is a separate, explicitly guarded development
command. With `ALLOW_DEVELOPMENT_DATA_POPULATION=true`, run:

```powershell
python -m app.development_population
```

It seeds the estate, scans the three controlled repositories with Semgrep, normalizes
the four seeded incidents, persists seven Signals, correlates four Candidates, and
commits the operation once. Stable provenance and Candidate identities make reruns
duplicate-safe or unchanged. It intentionally does not ingest the Git SATD or
dependency-lifecycle source and does not create TechnicalDebt or any human decision.

## Adding or Changing Persistent Data

Use this checklist for a focused persistence change:

1. Define the domain or application requirement and its invariant. Do not let a new
   column become the accidental definition of the concept.
2. Update or add the SQLAlchemy mapping under
   `backend/app/infrastructure/database/`.
3. Add one Alembic revision under `backend/alembic/versions/` with a safe `upgrade`
   and dependency-correct `downgrade`.
4. Update persistence functions and read models so they map the domain contract and
   preserve transaction ownership.
5. Add only the constraints that the current behavior requires: foreign keys,
   stable-key or provenance uniqueness, controlled values, ordering, or lifecycle
   integrity.
6. Change the controlled seed only when the baseline estate itself needs that data.
   Keep seed changes separate from structural migrations.
7. Add or update domain, persistence, migration, idempotency, and MSSQL integration
   tests in proportion to the behavior changed.
8. Run the relevant automated tests, then apply `alembic upgrade head` to a configured
   MSSQL database and verify the affected read/write path.

When extending a lifecycle, keep distinct records distinct. In particular, do not add
validation state to Signals, treat Candidate creation as TechnicalDebt registration,
collapse approval into policy authorization, or use verification as an implicit
TechnicalDebt status transition unless that transition is explicitly designed and
implemented.

## Related Documentation

- [Database Overview](database-overview.md)
- [Database Schema and Persistence](database-schema-and-persistence.md)
- [Data Lifecycle](data-lifecycle.md)
- [Architecture Decisions](../02-architecture/architecture-decisions.md)
