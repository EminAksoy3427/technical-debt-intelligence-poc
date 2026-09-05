# API contract — current implementation

Baseline: 5 September 2026. Application resources use `/api/v1` by default
(`Settings.api_v1_prefix`). The current Nuxt client calls that prefix explicitly.

## Executable contract

FastAPI's generated OpenAPI document at **`/openapi.json`** is the detailed
request/response schema source of truth. The running app also exposes Swagger UI
at **`/docs`** and ReDoc at **`/redoc`**. `backend/app/main.py` uses FastAPI's
default documentation routes. These paths are on the FastAPI origin, outside
the application resource prefix.

Pydantic response models live in `backend/app/api/v1/candidate_schemas.py`,
`backend/app/api/v1/connector_schemas.py`, and `router.py`. Frontend wire types
currently live in `frontend/app/types/candidateApi.ts` and
`frontend/app/types/connectorApi.ts`; automatic client generation is not claimed.

## Implemented routes

| Method and path | Purpose and response |
| --- | --- |
| `GET /api/v1/health` | Liveness response: HTTP 200 with `{"status":"ok"}`; does not check database readiness |
| `GET /api/v1/candidates` | Read all persisted Candidate summaries as `CandidateListResponse`: `items` and `count` |
| `GET /api/v1/candidates/{candidate_id}` | Read one Candidate by UUID as `CandidateDetailResponse` |
| `GET /api/v1/connectors` | Read registered connector inventory as `ConnectorListResponse`: `items` and `count` |

The Candidate list includes Candidate identity/hypothesis, canonical asset, enterprise
asset facts, and Signal/Evidence counts. Results are ordered by canonical asset
key, hypothesis and Candidate ID. An empty collection returns
`{"items":[],"count":0}`. No server-side pagination or filtering parameters are
implemented; Candidate Pool filtering is client-side.

Detail includes the Candidate's exact Signal/Evidence membership, hypothesis,
correlation rationale and provenance, plus enterprise and dependency context.
Enterprise context contains the asset, recorded ownerships/teams, direct
relationships and incidents. Dependency context includes anchors, direct
dependencies/dependents and reachable dependents.

`GET /api/v1/connectors` returns descriptor metadata from the in-code Connector
Registry. Each item exposes `connector_id`, `display_name`, `version`,
`source_system`, `transport`, `read_only`, and `status`. `status` is always
`registered`, meaning the connector is present in the application composition
registry. It does not mean source health, current availability, or successful
ingestion. Listing connectors does not execute them, does not call GitHub, does
not read local source files, and does not query MSSQL. Registry order is
preserved. An empty registry returns `{"items":[],"count":0}`. There is no
connector detail route and no POST/PUT/PATCH/DELETE connector API.

Runtime error behavior:

- Unknown Candidate UUID: HTTP 404, `{"detail":"Candidate not found"}`.
- Malformed Candidate UUID: HTTP 422 request validation error.
- Detected Candidate read-integrity failures: HTTP 500,
  `{"detail":"Persisted Candidate data failed integrity validation"}`.

The generated OpenAPI describes response models and UUID validation; the
explicit runtime 404/500 errors are not separately declared as response schemas
in the route decorators. See `backend/tests/api/test_candidate_api.py` and
`backend/tests/api/test_connector_api.py` for their executable behavior.

## Domain semantics and boundaries

Candidate routes read persisted hypotheses and supporting facts. They do not
ingest, correlate, validate debt, assign ownership, accept risk, execute actions
or close debt. GET reads do not commit or mutate persisted data.

Candidate is not TechnicalDebt; Evidence is not validation. Asset criticality
is not risk. Dependency reachability is not guaranteed outage or causal impact.
Recorded enterprise ownerships are context, not suggested teams or a Candidate
ownership decision. No Candidate risk/effort scores, governance status, agent
assessment or lifecycle endpoints are implemented.

Registered is not healthy. Connector inventory is composition metadata, not a
runtime health dashboard and not proof of successful acquisition.

The Candidate routers delegate database work to the infrastructure Candidate
read model; they do not issue SQL themselves. `candidate_schemas` also maps
infrastructure DTOs. Connector listing reads registry descriptors only and does
not use the database. These are known current dependencies, not a completed
application-port boundary. See the [architecture overview](architecture/overview.md)
and [domain invariants](domain/invariants.md).

Browser access uses settings-backed `CORS_ALLOWED_ORIGINS`, with GET/HEAD/OPTIONS,
Accept headers and no CORS credentials. CORS configuration does not implement
lifecycle authorization. Candidate reads need configured database access;
health, OpenAPI, and connector inventory do not.

## Contract verification

From `backend`, with development dependencies installed:

```text
python -m pytest tests/api/test_openapi_contract.py tests/api/test_candidate_api.py tests/api/test_connector_api.py tests/test_health.py
```

These existing tests verify HTTP/OpenAPI behavior using an isolated in-memory
SQLite fixture for Candidate reads; they do not require a live MSSQL database.
Connector inventory tests do not require a database or GitHub network access.
