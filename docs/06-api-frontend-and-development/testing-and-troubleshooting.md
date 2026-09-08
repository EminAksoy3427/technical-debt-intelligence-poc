# Testing and Troubleshooting

## Testing Strategy

The repository uses Pytest for the backend and Vitest for the frontend.

| Layer | Current coverage |
|---|---|
| Backend domain and unit tests | Domain invariants, normalization, correlation, governance transitions, action behavior, providers, and runtime policy. |
| Backend API and contract tests | Route behavior, error mapping, CORS, server-owned authority fields, and the generated OpenAPI contract. |
| Persistence and database tests | SQLAlchemy mapping/read-model tests plus opt-in MSSQL connectivity, migration, seed, ingestion, governance, and action tests. |
| Agent and provider tests | Runtime, tools, audit, deterministic behavior, mocked OpenAI adapter behavior, and an opt-in live OpenAI smoke test. |
| Connector and external tests | Connector contracts and registry behavior, mocked GitHub transport, and an optional public GitHub read test. |
| Evaluation tests | Correlation results and isolation of evaluation ground truth from runtime code and persistence. |
| Frontend unit/component tests | API adapters, type-to-presentation mappings, filters, view states, navigation, pages, validation, investigation, and action-workbench behavior. |

## Backend Tests

From `backend/` with the development dependencies installed:

```powershell
python -m pytest
python -m ruff check .
```

Useful focused commands include:

```powershell
python -m pytest tests/api/test_openapi_contract.py
python -m pytest tests/agent
python -m pytest tests/governance tests/actions
```

Pytest discovers `backend/tests/` from `backend/pyproject.toml`. Ruff checks the
configured Python error, import, and upgrade rules; no separate backend build command
is configured.

## Frontend Tests

From `frontend/`:

```powershell
npm run test
npm run typecheck
npm run build
```

These commands run Vitest, Nuxt/Vue type checking, and a production-mode Nuxt build.
There is no frontend lint script in the current `package.json`.

## Integration Tests

- Tests marked `integration` use MSSQL and skip when `DATABASE_URL` is absent. If the
  variable is present, it must identify a reachable, migrated SQL Server database.
- The public GitHub Issues test is marked `external` and skips when
  `GITHUB_REPOSITORY_OWNER` or `GITHUB_REPOSITORY_NAME` is not configured.
- The paid OpenAI smoke test runs only when `RUN_OPENAI_LIVE_TEST=1`,
  `AGENT_PROVIDER=openai`, and both `OPENAI_API_KEY` and `OPENAI_MODEL` are set.
- Normal executor, verifier, and OpenAI adapter tests use bounded fakes or mocked
  clients. There is no automated test that should create a GitHub Issue by default.

Because Pytest does not exclude marked tests by default, a configured external or
database environment may activate those tests during the full suite.

## Common Problems

### MSSQL connection failure

- Confirm SQL Server is running and the database already exists.
- Check that `DATABASE_URL` uses `mssql+pyodbc`, not another SQLAlchemy dialect.
- Confirm Microsoft ODBC Driver 17 for SQL Server is installed and its name matches
  the connection URL.
- Run `alembic current` and `alembic upgrade head` from `backend/`.
- Check `DATABASE_CONNECTION_TIMEOUT_SECONDS` if the server is reachable but slow.

### Frontend cannot reach the backend

- Set `NUXT_PUBLIC_API_BASE_URL=http://localhost:8000` in `frontend/.env`; the API
  composables fail closed when this value is blank.
- Confirm Uvicorn is running and `/api/v1/health` responds.
- Add `http://localhost:3000` to the backend's JSON-formatted
  `CORS_ALLOWED_ORIGINS`. Wildcard origins are rejected.
- Restart both development servers after changing their `.env` files.

### Candidate list is empty

Migrations and the enterprise seed do not create Candidates. Set
`ALLOW_DEVELOPMENT_DATA_POPULATION=true` and run
`python -m app.development_population` from `backend/`. The command requires the
Semgrep executable installed by the backend development dependencies.

### Agent provider unavailable

Use the default `AGENT_PROVIDER=deterministic` for local development without a model
credential. For the OpenAI adapter, configure the provider, API key, and model
together. The browser cannot choose or repair provider configuration, and the live
test remains disabled unless `RUN_OPENAI_LIVE_TEST=1` is explicitly set.

### Human Validation or governed actions are unavailable

- Candidate decisions require `HUMAN_GOVERNANCE_ENABLED=true` and a nonblank
  `HUMAN_GOVERNANCE_ACTOR_REFERENCE`.
- Proposal preparation requires the actor reference and both GitHub target fields.
- Approval and execution additionally require `HUMAN_ACTION_EXECUTION_ENABLED=true`.
- Real execution and verification require `GITHUB_ISSUE_EXECUTOR_TOKEN`; policy also
  requires the proposal target to match the configured target.

Approval does not bypass policy. If execution returns `UNKNOWN`, do not repeat the
write; use the verification/reconciliation operation.

### GitHub read integration is unavailable

The Connector inventory is always registration metadata. A live read additionally
requires the read-specific repository owner and name. Those settings are separate
from the governed-action target and executor token.

## Before Committing

- Run the relevant focused backend and frontend tests.
- Run the full backend suite and `python -m ruff check .` when Python is available.
- Run `npm run test`, `npm run typecheck`, and `npm run build` for frontend changes.
- Add an Alembic revision and exercise `alembic upgrade head` for schema changes.
- Run `git diff --check` and review the final diff for secrets and unrelated edits.
- Update documentation and API/frontend types when a contract changes.

## Related Documentation

- [Local Development](local-development.md)
- [Extending the System](extending-the-system.md)
- [Handover Guide](../07-handover-and-roadmap/handover-guide.md)
