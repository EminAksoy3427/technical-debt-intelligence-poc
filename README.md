# Technical Debt Intelligence & Governance PoC

Turn source observations into evidence-supported Candidates for human review.
**AI proposes. Evidence explains. Human decides.** A Signal is not a Candidate,
and a Candidate is not validated TechnicalDebt.

## Current PoC

The implementation is a **layered modular monolith** with deterministic
multi-source ingestion and Candidate correlation, persisted enterprise context,
and a Candidate Pool/Detail UI using real FastAPI read APIs.

```text
Sources → adapters → source-specific normalization → NormalizedSignal
        → deterministic Candidate correlation → persistence/read model
        → FastAPI → Nuxt Candidate Pool / Detail
```

Stack: Python 3.12 baseline (package requires >=3.12), FastAPI, synchronous
SQLAlchemy 2, Alembic, MSSQL via pyodbc; Nuxt 4 / Vue / TypeScript.
Frontend configuration requires Node >=22.12.0.

**Option B is the target:** an extensible modular monolith with Ports & Adapters,
explicit extension contracts, a governed agent runtime, and async-ready seams.
Those contracts and runtime are not implemented today. Neither is a
TechnicalDebt lifecycle. See the [architecture overview](docs/architecture/overview.md).

## Repository entry points

| Location | Purpose |
| --- | --- |
| [backend/app/main.py](backend/app/main.py) | FastAPI application: `app.main:app` |
| [backend/app/domain](backend/app/domain) | Signal, Evidence, Candidate and enterprise context semantics |
| [backend/app](backend/app) | Source-specific ingestion and deterministic correlation |
| [backend/app/infrastructure](backend/app/infrastructure) | Source adapters, persistence and Candidate read model |
| [backend/alembic](backend/alembic) | Migrations; configuration in `backend/alembic.ini` |
| [frontend/app/app.vue](frontend/app/app.vue) | Nuxt entry; routes in `frontend/app/pages` |
| [backend/tests](backend/tests) / [frontend/tests/unit](frontend/tests/unit) | Backend tests and frontend Vitest tests |
| [synthetic_repositories](synthetic_repositories) / [synthetic_sources](synthetic_sources) | Controlled source inputs |
| [evaluation](evaluation/README.md) | Evaluation-only fixtures, separate from runtime inputs |
| [docs](docs) | Architecture, domain, decisions and API baseline |

## Run and test entry points

With dependencies already installed in the chosen environment, run from `backend`:

```text
python -m uvicorn app.main:app --reload
python -m pytest tests/api/test_openapi_contract.py tests/api/test_candidate_api.py tests/test_health.py
```

Backend dependencies and test configuration are in
[pyproject.toml](backend/pyproject.toml). Database operations require the
environment-backed configuration described in [backend/.env.example](backend/.env.example).
External-infrastructure tests are marked `integration`.

From `frontend`, `npm run dev` starts Nuxt and `npm test` runs Vitest, as defined
in [package.json](frontend/package.json). Configure `NUXT_PUBLIC_API_BASE_URL`
as the FastAPI origin and backend `CORS_ALLOWED_ORIGINS` for browser access;
see [frontend/.env.example](frontend/.env.example). A missing API base URL
produces an explicit error; there is no runtime mock fallback.

Current routes: `GET /api/v1/health`, `GET /api/v1/candidates`, and
`GET /api/v1/candidates/{candidate_id}`. Detailed executable contracts are served
at `/openapi.json` and browsable at `/docs` on the running FastAPI app.

## Deeper documentation

- [Architecture: current, Option B target, database and frontend baseline](docs/architecture/overview.md)
- [Domain invariants and terminology](docs/domain/invariants.md)
- [ADR 0001: Option B — Extensible Modular Monolith](docs/adr/0001-option-b-extensible-modular-monolith.md)
- [Current API contract](docs/api-contract.md)
