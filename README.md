# Technical Debt Intelligence & Governance PoC

Turn source observations into evidence-supported Candidates for human review,
then into REGISTERED TechnicalDebt and a governed external action.
**AI proposes. Evidence explains. Human decides.** A Signal is not a Candidate,
a Candidate is not validated TechnicalDebt, and REGISTERED TechnicalDebt is not
remediation approved, scheduled, or resolved.

## Current PoC

The implementation is a **layered modular monolith** with deterministic
multi-source ingestion and Candidate correlation, persisted enterprise context,
a governed Agent Investigation plane, a Human Validation command plane that can
register TechnicalDebt, a governed L3/L4 GitHub issue action plane, and Nuxt
workspaces for Overview, Candidates, Technical Debts, and Sources.

```text
Sources → adapters → source-specific normalization → NormalizedSignal
        → deterministic Candidate correlation → persistence/read model
        → FastAPI → Nuxt Candidate Pool / Detail

READ / investigation plane:
  Nuxt Agent Investigation → FastAPI AgentRun → AgentRuntime
    → Tool Registry → Policy → Candidate READ tools

Human governance command plane (not behind AgentRuntime):
  Nuxt Human Validation / Technical Debts → FastAPI
    → apply_human_validation → domain / persistence → MSSQL

Governed action plane (not an Agent Tool, not the GitHub READ connector):
  Nuxt TechnicalDebt Detail
    → L3 ActionProposal preparation
    → L4 human approval
    → dedicated action-execution policy
    → GitHub Issue Executor (POST create, no retry)
    → GitHub Issue Verifier (GET-only read-back)
    → persisted audit trail
```

Stack: Python 3.12 baseline (package requires >=3.12), FastAPI, synchronous
SQLAlchemy 2, Alembic, MSSQL via pyodbc; Nuxt 4 / Vue / TypeScript.
Frontend configuration requires Node >=22.12.0.

**Option B is the target:** an extensible modular monolith with Ports & Adapters,
explicit extension contracts, a governed agent runtime, and async-ready seams.
This remains one application, not microservices.

Connector, SourceObservation, and Connector Registry contracts exist for
registered sources. Candidate-scoped READ tools, Tool Registry, Policy, and a
bounded Agent Runtime persist AgentRun audit. Human Validation persists
HumanDecision history, derives Candidate governance, and atomically creates
exactly one REGISTERED TechnicalDebt on VALIDATE. The server-owned PoC actor
seam (`HUMAN_GOVERNANCE_ENABLED`, `HUMAN_GOVERNANCE_ACTOR_REFERENCE`) is not
enterprise authentication. MSSQL remains the system of record.

Day 5 adds server-prepared immutable `CREATE_GITHUB_ISSUE` ActionProposals,
append-only L4 ActionApproval, a dedicated Action Execution Policy (separate
from Agent Tool Policy), one-shot GitHub issue execution with
IN_PROGRESS / SUCCEEDED / FAILED / UNKNOWN outcomes, GET-only verification
and marker reconciliation, and a TechnicalDebt Detail workbench. AI does not
autonomously authorize or perform external writes.

The governed GitHub write **capability exists**. Package development, tests,
and browser smoke did **not** perform a live GitHub write. Capability
implemented is not the same as a live demo executed.

See the [architecture overview](docs/architecture/overview.md) and the
[Day 5 checkpoint](docs/checkpoints/day-5-governed-action-execution.md).

## Current end-to-end lifecycle

```text
Sources → Signal + Evidence → Candidate
  → Human Validation
       VALIDATE     → VALIDATED + exactly one REGISTERED TechnicalDebt
       REJECT       → REJECTED, no TechnicalDebt
       REQUEST_INFO → INFORMATION_REQUESTED, no TechnicalDebt
  → L3 Action Preparation → immutable ActionProposal
  → Human L4 Approval → ActionApproval
  → dedicated Action Execution Policy → ActionPolicyDecision
  → ActionExecution → external GitHub create (one attempt)
  → ActionVerification → persisted audit trail
```

Human Validation classifies a Candidate. It is not L4 Action Approval.
ActionProposal is a prepared preview, not authorization. Policy ALLOW is not
successful execution. External create success is not verification. Verification
is not TechnicalDebt closure. REGISTERED remains the only TechnicalDebt
lifecycle status.

## Repository entry points

| Location | Purpose |
| --- | --- |
| [backend/app/main.py](backend/app/main.py) | FastAPI application: `app.main:app` |
| [backend/app/domain](backend/app/domain) | Signal, Evidence, Candidate, HumanDecision, TechnicalDebt, ActionProposal, ActionApproval, ActionPolicyDecision, ActionExecution, ActionVerification, and enterprise context |
| [backend/app/governance](backend/app/governance) | Human Validation contracts, transitions, and application service |
| [backend/app/actions](backend/app/actions) | L3 preparation, L4 approval, action-execution policy, execution, verification, and GitHub action-plane ports |
| [backend/app](backend/app) | Source-specific ingestion and deterministic correlation |
| [backend/app/connectors](backend/app/connectors) | Acquisition-plane Connector Registry, including GitHub Issues READ |
| [backend/app/infrastructure](backend/app/infrastructure) | Source adapters, persistence, read models, GitHub Issue Executor, and GitHub Issue Verifier |
| [backend/alembic](backend/alembic) | Migrations; configuration in `backend/alembic.ini` |
| [frontend/app/app.vue](frontend/app/app.vue) | Nuxt entry; routes in `frontend/app/pages` |
| [backend/tests](backend/tests) / [frontend/tests/unit](frontend/tests/unit) | Backend tests and frontend Vitest tests |
| [synthetic_repositories](synthetic_repositories) / [synthetic_sources](synthetic_sources) | Controlled source inputs |
| [evaluation](evaluation/README.md) | Evaluation-only fixtures, separate from runtime inputs |
| [docs](docs) | Architecture, domain, decisions, API, and checkpoints |

## Run and test entry points

With dependencies already installed in the chosen environment, run from `backend`:

```text
python -m uvicorn app.main:app --reload
python -m pytest tests/api/test_openapi_contract.py tests/api/test_candidate_api.py tests/test_health.py
python -m pytest -m "not integration and not external"
```

Backend dependencies and test configuration are in
[pyproject.toml](backend/pyproject.toml). Database operations require the
environment-backed configuration described in [backend/.env.example](backend/.env.example).
Tests that need live MSSQL are marked `integration`. Tests that need a live
external HTTP source are marked `external`. The deterministic suite excludes
both markers and must not require Internet access. Do not run real GitHub
write tests as part of ordinary local verification.

Agent investigations default to `AGENT_PROVIDER=deterministic`, which requires
no OpenAI configuration. Live inference requires server-side
`AGENT_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL`; the API and browser
cannot select the provider or model. The model only proposes existing READ tool
calls. The Registry, Policy, and bounded Runtime authorize and execute them, and
raw prompts, model responses, and reasoning are not persisted. After live
settings are configured, the explicitly paid smoke test is:

```text
RUN_OPENAI_LIVE_TEST=1 python -m pytest -m external tests/integration/test_openai_provider_live.py
```

Human Validation is disabled by default. Enabling it requires server-side
`HUMAN_GOVERNANCE_ENABLED=true` and `HUMAN_GOVERNANCE_ACTOR_REFERENCE`. L4
approval and execution use a separate `HUMAN_ACTION_EXECUTION_ENABLED` seam.
`HUMAN_GOVERNANCE_ENABLED` does not enable L4. The configured actor value is
opaque audit attribution, not a verified employee.

L3 preparation needs the server-owned demo target
`GITHUB_ISSUE_TARGET_REPOSITORY_OWNER` and
`GITHUB_ISSUE_TARGET_REPOSITORY_NAME`. Those values are not write authority.
The dedicated execution-plane credential is `GITHUB_ISSUE_EXECUTOR_TOKEN`
(`SecretStr`). It is never returned through API or frontend. Policy DENY
produces zero external writes when execution is disabled or the executor is
not ready.

From `frontend`, `npm run dev` starts Nuxt and `npm test` runs Vitest, as defined
in [package.json](frontend/package.json). Configure `NUXT_PUBLIC_API_BASE_URL`
as the FastAPI origin and backend `CORS_ALLOWED_ORIGINS` for browser access;
see [frontend/.env.example](frontend/.env.example). A missing API base URL
produces an explicit error; there is no runtime mock fallback.

Current API routes include Candidate reads and AgentRun, Human Validation
`POST /api/v1/candidates/{candidate_id}/human-decisions`, TechnicalDebt
list/detail, governed action preparation/approval/execution/verification,
connectors, and health. Current frontend routes: `/overview`
(product landing), `/candidates` (Candidate review queue), `/candidates/[id]`
(Overview, Evidence & Context, AI Investigation as decision support, and
Human Validation as the authoritative governance boundary),
`/technical-debts` (governed TechnicalDebt records created through VALIDATE),
`/technical-debts/[id]` (provenance, Action Preparation, L4 workbench, and
audit trail), and `/sources` (registered connector inventory and implemented
Signal ingestion capabilities). Registration is not runtime health, and the
Connector Registry is not 1:1 with Signal ingestion. Semgrep, Git SATD,
Incident management, and Dependency lifecycle currently produce
NormalizedSignal; GitHub Issues is acquisition-only and is not the GitHub
Issue Executor. `/` redirects to `/overview`. Detailed executable contracts
are served at `/openapi.json` and browsable at `/docs` on the running FastAPI
app.

Synthetic repositories, synthetic sources, and the development population
command remain demo/control surfaces. They are not production ingestion and
do not prove a live GitHub write.

## Deeper documentation

- [Architecture: current, Option B target, database and frontend baseline](docs/architecture/overview.md)
- [Adding a connector](docs/extensions/adding-a-connector.md)
- [Database evolution and migrations](docs/database/evolution-and-migrations.md)
- [Domain invariants and terminology](docs/domain/invariants.md)
- [ADR 0001: Option B — Extensible Modular Monolith](docs/adr/0001-option-b-extensible-modular-monolith.md)
- [Current API contract](docs/api-contract.md)
- [Day 5 checkpoint: governed action execution](docs/checkpoints/day-5-governed-action-execution.md)
- [Day 4 checkpoint: Human Validation and TechnicalDebt](docs/checkpoints/day-4-human-validation-technical-debt.md)
