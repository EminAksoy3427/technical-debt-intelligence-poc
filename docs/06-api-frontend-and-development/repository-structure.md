# Repository Structure

## Top-Level Structure

```text
technical-debt-intelligence-poc/
├── backend/                 FastAPI application, migrations, rules, and tests
├── frontend/                Nuxt governance workspace and frontend tests
├── docs/                    Current system documentation
├── evaluation/              Independent correlation ground truth and evaluation notes
├── synthetic_repositories/  Controlled repositories containing test findings
├── synthetic_sources/       Controlled source records, including dependency lifecycle data
├── README.md                Project overview
└── AGENTS.md                Repository development rules
```

Generated directories such as `backend/.venv/`, `frontend/node_modules/`,
`frontend/.nuxt/`, and `frontend/.output/` are local artifacts, not architectural
modules.

## Backend Structure

The backend is an extensible modular monolith. There is no generic
`backend/app/application/` package; use-case orchestration lives in the capability
modules below.

| Area | Responsibility |
|---|---|
| `backend/app/domain/` | Domain values and invariants for facts, Candidates, governance, and actions. |
| `backend/app/api/` | FastAPI routes, transport contracts, dependency wiring, and HTTP error mapping. |
| `backend/app/connectors/` | Read-only Connector contracts, implementations, and explicit registration. |
| `backend/app/agent/` | Investigation runtime, tools, policy, provider boundary, providers, and audit contracts. |
| `backend/app/governance/` | Human-validation commands and Candidate governance transitions. |
| `backend/app/actions/` | Proposal, approval, execution policy, executor/verifier ports, execution, and verification. |
| `backend/app/infrastructure/` | Semgrep, Git, GitHub, controlled-source, and database adapters. |
| `backend/app/infrastructure/database/` | SQLAlchemy models, persistence functions, read models, seed, and database composition. |
| `backend/app/*_ingestion.py` | Source-specific normalization and ingestion orchestration. |
| `backend/app/candidate_correlation.py` | Deterministic Candidate correlation. |
| `backend/alembic/` | Ordered MSSQL schema revisions. |
| `backend/semgrep/` | Repository-controlled Semgrep rules. |
| `backend/tests/` | Backend unit, API, evaluation, infrastructure, and opt-in integration tests. |

## Frontend Structure

| Area | Responsibility |
|---|---|
| `frontend/app/pages/` | Overview, Sources, Candidate, and TechnicalDebt routes. |
| `frontend/app/components/` | Workflow presentation grouped by Candidate, TechnicalDebt, source, overview, and navigation concerns. |
| `frontend/app/composables/` | FastAPI clients for Candidates, Connector inventory, AgentRuns, Human Validation, and TechnicalDebt actions. |
| `frontend/app/types/` | API wire types and separate presentation types. |
| `frontend/app/utils/` | Mapping, display-state, filtering, request-building, and submission helpers. |
| `frontend/app/layouts/` | Application shell layout. |
| `frontend/app/assets/` | Shared frontend styling. |
| `frontend/tests/unit/` | Vitest coverage for API clients, mappings, view state, pages, and workflow components. |

## Data and Evaluation Assets

- `backend/alembic/versions/` contains the versioned database schema.
- `backend/app/domain/synthetic_enterprise_estate.py` defines the controlled estate;
  `backend/app/infrastructure/database/enterprise_estate_seed.py` materializes it.
- `synthetic_repositories/` contains the local repositories scanned by Semgrep and
  used by Git-history tests.
- `synthetic_sources/dependency_lifecycle_findings.json` is the controlled dependency
  lifecycle input.
- `evaluation/ground_truth/correlation_cases.json` is an independent evaluation
  oracle and must not be loaded by runtime code or seed logic.

## Where Do I Change...?

| Task | Start Here |
|---|---|
| Add a source | `backend/app/connectors/contracts.py`, the relevant adapter under `backend/app/infrastructure/`, and `backend/app/connectors/registry.py` |
| Add or change Signal normalization | The relevant `backend/app/*_ingestion.py` module and `backend/app/domain/signals.py` |
| Change Candidate behavior | `backend/app/candidate_correlation.py` and `backend/app/domain/candidates.py` |
| Modify the database schema | `backend/app/infrastructure/database/*_models.py` and a new revision in `backend/alembic/versions/` |
| Add an Agent tool | `backend/app/agent/candidate_tools.py`, `backend/app/agent/composition.py`, and the reader boundary in `backend/app/agent/ports.py` |
| Add or replace an AI provider | `backend/app/agent/runtime_contracts.py`, a provider adapter under `backend/app/agent/`, and `backend/app/agent/provider_composition.py` |
| Change Human Validation | `backend/app/governance/`, then the Candidate API schemas and frontend validation workflow |
| Change action policy | `backend/app/actions/execution_policy.py` |
| Add an executor or verifier | Protocols in `backend/app/actions/` and adapters in `backend/app/infrastructure/` |
| Add a backend route | `backend/app/api/v1/` and `backend/app/api/v1/router.py` |
| Add a frontend screen | `frontend/app/pages/`, with components, API types/composables, mappings, and tests as needed |
| Update backend tests | The matching capability directory under `backend/tests/` |
| Update frontend tests | `frontend/tests/unit/` |

## Related Documentation

- [Local Development](local-development.md)
- [Extending the System](extending-the-system.md)
- [Module Boundaries](../02-architecture/module-boundaries.md)
