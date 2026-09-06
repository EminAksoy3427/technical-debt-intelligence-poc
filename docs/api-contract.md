# API contract — current implementation

Baseline: 6 September 2026, Day 4. Application resources use `/api/v1` by default
(`Settings.api_v1_prefix`). The current Nuxt client calls that prefix explicitly.

## Executable contract

FastAPI's generated OpenAPI document at **`/openapi.json`** is the detailed
request/response schema source of truth. The running app also exposes Swagger UI
at **`/docs`** and ReDoc at **`/redoc`**. `backend/app/main.py` uses FastAPI's
default documentation routes. These paths are on the FastAPI origin, outside
the application resource prefix.

Pydantic response models live in `backend/app/api/v1/candidate_schemas.py`,
`backend/app/api/v1/agent_run_schemas.py`,
`backend/app/api/v1/human_decision_schemas.py`,
`backend/app/api/v1/technical_debt_schemas.py`,
`backend/app/api/v1/connector_schemas.py`, and `router.py`. Frontend wire types
currently live in `frontend/app/types/candidateApi.ts`,
`frontend/app/types/humanValidationApi.ts`,
`frontend/app/types/technicalDebtApi.ts`,
`frontend/app/types/connectorApi.ts`, and `frontend/app/types/agentRunApi.ts`;
automatic client generation is not claimed.

## Implemented routes

| Method and path | Purpose and response |
| --- | --- |
| `GET /api/v1/health` | Liveness response: HTTP 200 with `{"status":"ok"}`; does not check database readiness |
| `GET /api/v1/candidates` | Read all persisted Candidate summaries as `CandidateListResponse`: `items` and `count` |
| `GET /api/v1/candidates/{candidate_id}` | Read one Candidate by UUID as `CandidateDetailResponse`, including derived `governance` |
| `POST /api/v1/candidates/{candidate_id}/human-decisions` | Apply one Human Validation command; HTTP 201 `HumanValidationResponse` |
| `POST /api/v1/candidates/{candidate_id}/agent-runs` | Run the server-owned bounded investigation and return the persisted `AgentRunResponse`: HTTP 201 |
| `GET /api/v1/candidates/{candidate_id}/agent-runs/{agent_run_id}` | Read one persisted Candidate-scoped `AgentRunResponse` aggregate |
| `GET /api/v1/technical-debts` | Read REGISTERED TechnicalDebt summaries as `TechnicalDebtListResponse`: `items` and `count` |
| `GET /api/v1/technical-debts/{technical_debt_id}` | Read one TechnicalDebt by UUID as `TechnicalDebtDetailResponse` |
| `GET /api/v1/connectors` | Read registered connector inventory as `ConnectorListResponse`: `items` and `count` |

The Candidate list includes Candidate identity/hypothesis, canonical asset, enterprise
asset facts, and Signal/Evidence counts. Results are ordered by canonical asset
key, hypothesis and Candidate ID. An empty collection returns
`{"items":[],"count":0}`. No server-side pagination or filtering parameters are
implemented; Candidate Pool filtering is client-side. List items do not include
governance.

Detail includes the Candidate's exact Signal/Evidence membership, hypothesis,
correlation rationale and provenance, plus enterprise and dependency context.
Enterprise context contains the asset, recorded ownerships/teams, direct
relationships and incidents. Dependency context includes anchors, direct
dependencies/dependents and reachable dependents.

Candidate Detail also includes derived `governance`:

- `state` — `PENDING`, `INFORMATION_REQUESTED`, `VALIDATED`, or `REJECTED`
- `revision` — `0` with no decisions; otherwise the latest HumanDecision
  `sequence_number`
- `decisions` — append-only HumanDecision history
- `technical_debt` — the REGISTERED TechnicalDebt when one exists, otherwise
  `null`

Governance is not a Candidate table column. The client cannot write `state`,
`revision`, or resulting TechnicalDebt identity.

### Human Validation command

`POST /api/v1/candidates/{candidate_id}/human-decisions` accepts only untrusted
intent fields:

- `decision`
- `rationale`
- `requested_information`
- `expected_governance_revision`

`additionalProperties` is false. The client cannot submit `actor_reference`,
`role`, `approval`, `authorization`, `provider`, `model`, `tool`,
`technical_debt_id`, or a resulting state. Actor identity comes from server
settings when Human Governance is enabled.

There is no silent idempotency. A duplicate or stale command is a conflict.

### TechnicalDebt reads

List items expose TechnicalDebt identity, `REGISTERED` status, created time,
source Candidate identity, hypothesis, and canonical asset. Detail adds source
Candidate rationale and the creation VALIDATE HumanDecision. Evidence remains
owned and read through Candidate provenance. These routes do not invent risk,
effort, owner, priority, target date, remediation plan, verification, or
closure.

`GET /api/v1/connectors` returns descriptor metadata from the in-code Connector
Registry. Each item exposes `connector_id`, `display_name`, `version`,
`source_system`, `transport`, `read_only`, and `status`. `status` is always
`registered`, meaning the connector is present in the application composition
registry. It does not mean source health, current availability, or successful
ingestion. Listing connectors does not execute them, does not call GitHub, does
not read local source files, and does not query MSSQL. Registry order is
preserved. An empty registry returns `{"items":[],"count":0}`. There is no
connector detail route and no POST/PUT/PATCH/DELETE connector API.

## Status behavior

Route-specific behavior currently implemented:

- Human Validation success: HTTP 201.
- Human Governance disabled: HTTP 403,
  `{"detail":"Human Validation is not available"}`.
  If `HUMAN_GOVERNANCE_ENABLED=true`, Settings requires a nonblank
  `HUMAN_GOVERNANCE_ACTOR_REFERENCE`. Invalid enabled configuration is a
  configuration/startup validation issue, not a normal HTTP 403 route
  outcome.
- Unknown Candidate UUID: HTTP 404, `{"detail":"Candidate not found"}`.
- Unknown TechnicalDebt UUID: HTTP 404, `{"detail":"TechnicalDebt not found"}`.
- Stale expected revision, illegal transition, or recognized governance
  uniqueness conflict: HTTP 409 with the typed error message.
- Malformed UUID, extra request fields, or invalid Human Validation content:
  HTTP 422.
- Detected Candidate read-integrity failures: HTTP 500,
  `{"detail":"Persisted Candidate data failed integrity validation"}`.
- Detected TechnicalDebt read-integrity failures: HTTP 500,
  `{"detail":"Persisted TechnicalDebt data failed integrity validation"}`.
- Unknown AgentRun for the path Candidate, including a run owned by another
  Candidate: HTTP 404, `{"detail":"AgentRun not found"}`.
- A durably represented runtime failure is returned as an HTTP 201 resource
  with `status=FAILED`; `ABSTAINED` is also a valid HTTP 201 outcome.

This is not a generic API error framework. Explicit runtime 404/409/403/500
errors are not separately declared as response schemas in the route decorators.

AgentRun POST accepts no request body. Prompts, tool selections, scripted steps,
authorization controls, provider configuration and model settings are not part
of the public contract; a supplied body is rejected with HTTP 422. The server
selects the default deterministic provider or optional live OpenAI provider from
trusted configuration, then composes the Candidate READ Tool Registry, LOW-risk
READ authorization and runtime limits. The OpenAI adapter proposes tool calls
but never executes them.

AgentRun responses expose run state and timestamps, Structured Assessment,
ordered safe ToolExecution fields and ordered PolicyDecision audit facts. They
omit raw tool payloads, input hashes/summaries, raw prompts/provider responses,
hidden reasoning, settings, credentials and connection information. Policy
ALLOW/DENY records deterministic runtime policy, not human approval.

See `backend/tests/api/test_candidate_api.py`,
`backend/tests/api/test_human_decision_api.py`,
`backend/tests/api/test_technical_debt_api.py`,
`backend/tests/api/test_human_actor_context.py`, and
`backend/tests/api/test_connector_api.py` for executable behavior.

## Domain semantics and boundaries

Candidate routes read persisted hypotheses and supporting facts. They do not
ingest, correlate, assign ownership, accept risk, execute actions, or close
debt. GET reads do not commit or mutate persisted data.

Candidate is not TechnicalDebt; Evidence is not validation; StructuredAssessment
is not a HumanDecision. Asset criticality is not risk. Dependency reachability
is not guaranteed outage or causal impact. Recorded enterprise ownerships are
context, not suggested teams or a Candidate ownership decision. No Candidate
risk/effort scores are implemented.

Starting an AgentRun investigates a Candidate; it does not validate the
Candidate, create TechnicalDebt, authorize action, or establish causality/risk.
Every Structured Assessment remains evidence/tool-reference grounded and
requires a later authorized human decision. Runtime grounding validation remains
authoritative for deterministic and live provider output.

Human Validation classifies a Candidate. `VALIDATE` persists one HumanDecision
and atomically creates exactly one REGISTERED TechnicalDebt. `REJECT` and
`REQUEST_INFO` persist a HumanDecision and create no TechnicalDebt.
`REQUEST_INFO` leaves a later decision possible. Candidate, Evidence, and
Signals are not deleted. REGISTERED is not remediation approval, scheduled
work, or resolution.

Human Governance is disabled by default. When enabled, `actor_reference` is
server-owned opaque audit attribution. This is not OAuth, ADFS, SSO, JWT
enterprise identity, or reviewer RBAC. The configured actor is not a verified
employee.

Registered is not healthy. Connector inventory is composition metadata, not a
runtime health dashboard and not proof of successful acquisition.

The Candidate and TechnicalDebt routers delegate database work to infrastructure
persistence and composition functions; they do not issue SQL themselves.
`candidate_schemas` also maps infrastructure DTOs. Human Validation uses a
transaction-free Session so `apply_human_validation` can own BEGIN / COMMIT /
ROLLBACK. Connector listing reads registry descriptors only and does
not use the database. These are known current dependencies, not a completed
application-port boundary. See the [architecture overview](architecture/overview.md)
and [domain invariants](domain/invariants.md).

Browser access uses settings-backed `CORS_ALLOWED_ORIGINS`, with
GET/HEAD/OPTIONS/POST, Accept/Content-Type headers and no CORS credentials.
CORS configuration does not implement
lifecycle authorization. Candidate, Human Validation, and TechnicalDebt routes
need configured database access; health, OpenAPI, and connector inventory do not.

## Contract verification

From `backend`, with development dependencies installed:

```text
python -m pytest tests/api/test_agent_run_api.py tests/api/test_openapi_contract.py tests/api/test_candidate_api.py tests/api/test_human_decision_api.py tests/api/test_technical_debt_api.py tests/api/test_human_actor_context.py tests/api/test_connector_api.py tests/test_health.py
```

These tests verify HTTP/OpenAPI behavior using an isolated in-memory SQLite
fixture for Candidate reads, Human Validation writes, TechnicalDebt reads, and
AgentRun execution; they do not require a live MSSQL database and do not prove
MSSQL concurrency.
Connector inventory tests do not require a database or GitHub network access.
