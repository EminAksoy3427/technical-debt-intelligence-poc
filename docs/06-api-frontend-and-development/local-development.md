# Local Development

## Prerequisites

| Requirement | Current baseline |
|---|---|
| Python | Python 3.12 or newer, as declared by `backend/pyproject.toml` |
| Node.js | Node.js 22.12.0 or newer, as declared by `frontend/package.json` |
| Microsoft SQL Server | Required for migrations and all database-backed application workflows |
| ODBC driver | Microsoft ODBC Driver 17 for SQL Server is used by the repository examples |
| Git | Required by the Git-history scanner and its controlled repository tests |
| Semgrep | Installed by the backend `dev` dependency set and required by the development Candidate population command |

The commands below assume PowerShell and start from the repository root. The backend
and frontend each load their own `.env` file when run from their directory.

## Backend Setup

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Edit `backend/.env` and set at least `DATABASE_URL` for database-backed routes. For a
browser frontend at `http://localhost:3000`, also set:

```text
CORS_ALLOWED_ORIGINS=["http://localhost:3000"]
```

Apply the schema, optionally populate controlled Candidate data, and start FastAPI:

```powershell
alembic upgrade head
$env:ALLOW_DEVELOPMENT_DATA_POPULATION = "true"
python -m app.development_population
python -m uvicorn app.main:app --reload
```

The API is then available at `http://localhost:8000`; the versioned API prefix defaults
to `/api/v1`. The FastAPI application does not run migrations or seed data at startup.

## Database Setup

Create the SQL Server database before running Alembic. `DATABASE_URL` must use the
`mssql+pyodbc` dialect. `backend/.env.example` contains placeholder forms for Windows
integrated authentication and SQL authentication; do not commit a real connection
string.

From `backend/`, run:

```powershell
alembic upgrade head
```

Two current data commands serve different purposes:

- `python -m app.infrastructure.database.enterprise_estate_seed` creates or
  reconciles only the controlled assets, teams, ownerships, relationships, and
  incidents.
- `python -m app.development_population`, with
  `ALLOW_DEVELOPMENT_DATA_POPULATION=true`, also runs that seed, scans the controlled
  repositories with Semgrep, normalizes seeded incidents, and persists the four
  demonstration Candidates.

Both processes are duplicate-safe for their controlled baseline. Neither creates a
Human Decision or TechnicalDebt. See
[Migrations, Seeding and Data Model Extension](../03-data-and-database/migrations-seeding-and-extension.md)
for details.

## Frontend Setup

In another terminal, from the repository root:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
```

Set the public API origin in `frontend/.env`:

```text
NUXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

Start Nuxt:

```powershell
npm run dev
```

The development UI is available at `http://localhost:3000` by default.

## Running the Full PoC

1. Start SQL Server and confirm that the database named by `DATABASE_URL` exists.
2. From `backend/`, run `alembic upgrade head`, then run the guarded development
   population command if Candidate data is needed, and start Uvicorn.
3. From `frontend/`, configure `NUXT_PUBLIC_API_BASE_URL` and start `npm run dev`.
4. Configure OpenAI or GitHub only when those optional external paths are required.
   GitHub write execution is disabled by default.
5. Open `http://localhost:3000`, then verify the Candidate list and detail workflow.

## Environment Variables

Only server-owned settings belong in `backend/.env`. Important implemented settings
are:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | MSSQL SQLAlchemy connection URL used by routes, migrations, seed, and integration tests. |
| `DATABASE_CONNECTION_TIMEOUT_SECONDS` | Database connection timeout. |
| `CORS_ALLOWED_ORIGINS` | JSON array of explicit browser origins; wildcards are rejected. |
| `ALLOW_DEVELOPMENT_DATA_POPULATION` | Explicit guard for the controlled Candidate population command. |
| `AGENT_PROVIDER` | Selects `deterministic` (default) or `openai`. |
| `AGENT_MAX_ITERATIONS`, `AGENT_MAX_TOOL_CALLS`, `AGENT_RUN_TIMEOUT_SECONDS`, `AGENT_TOOL_TIMEOUT_SECONDS` | Bounds the investigation runtime. |
| `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_REQUEST_TIMEOUT_SECONDS` | Required provider settings when `AGENT_PROVIDER=openai`. |
| `HUMAN_GOVERNANCE_ENABLED`, `HUMAN_GOVERNANCE_ACTOR_REFERENCE` | Enables Candidate validation and supplies server-owned audit attribution. |
| `HUMAN_ACTION_EXECUTION_ENABLED` | Separately enables human action approval and the execution policy path. |
| `GITHUB_REPOSITORY_OWNER`, `GITHUB_REPOSITORY_NAME`, `GITHUB_REQUEST_TIMEOUT_SECONDS` | Configure the optional read-only GitHub Issues connector. |
| `GITHUB_ISSUE_TARGET_REPOSITORY_OWNER`, `GITHUB_ISSUE_TARGET_REPOSITORY_NAME` | Configure the server-owned governed-action target. |
| `GITHUB_ISSUE_EXECUTOR_TOKEN`, `GITHUB_ISSUE_EXECUTOR_CONNECT_TIMEOUT_SECONDS`, `GITHUB_ISSUE_EXECUTOR_REQUEST_TIMEOUT_SECONDS` | Configure the dedicated GitHub writer and read-back verifier. |
| `NUXT_PUBLIC_API_BASE_URL` | Frontend-visible FastAPI origin, configured in `frontend/.env`. |

Do not place real secrets in either example file or commit a populated `.env`.

## Quick Verification

- `Invoke-RestMethod http://localhost:8000/api/v1/health` returns `status` equal to
  `ok`.
- `http://localhost:3000` redirects to the Overview page and renders the application
  shell.
- The Candidate page loads the controlled Candidate collection after development
  population.
- `alembic current` reports the database at the latest applied revision.
- An investigation completes with the deterministic provider. OpenAI and GitHub
  behavior should be checked only when their explicit settings are present.

## Related Documentation

- [Testing and Troubleshooting](testing-and-troubleshooting.md)
- [Repository Structure](repository-structure.md)
- [Migrations, Seeding and Data Model Extension](../03-data-and-database/migrations-seeding-and-extension.md)
