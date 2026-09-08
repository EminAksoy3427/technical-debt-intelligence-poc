# Extending the System

## Extension Principles

1. Keep domain meaning and invariants in `backend/app/domain/` and the owning
   application capability.
2. Keep vendor-specific records, SDKs, transport, and credentials at external
   boundaries.
3. Preserve stable source identity, Evidence, and provenance through every Signal
   path.
4. Do not give read Connectors write authority; use a separate Executor boundary.
5. Keep AI advisory. Agent output must not perform Human Validation or create
   authoritative lifecycle state.
6. Keep human approval and deterministic policy authorization separate.
7. Verify external side effects through an independent read-back boundary.
8. Add contract, behavior, failure, and boundary tests with every capability.

## Common Extension Types

| I Want To... | Extension Point | Detailed Guide / Code Area |
|---|---|---|
| Add a new Signal source | Source adapter, Connector where applicable, source-specific normalizer, Signal persistence, and registration/composition | [Adding a New Connector](../04-signals-context-and-integrations/adding-a-new-connector.md); `backend/app/connectors/`, `backend/app/infrastructure/`, and `backend/app/*_ingestion.py` |
| Add a new Agent tool | Typed tool contract and implementation, explicit registry composition, policy metadata, database reader support, and tests | `backend/app/agent/candidate_tools.py`, `ports.py`, `composition.py`, and `backend/app/infrastructure/database/candidate_tool_composition.py` |
| Add a new AI provider | `InvestigationProvider` implementation and server-owned provider composition | `backend/app/agent/runtime_contracts.py`, `provider_composition.py`, and the current adapters in `backend/app/agent/` |
| Add a new governed action | Domain action type and payload, persistence, proposal/approval/policy/execution/verification orchestration, API/frontend contract, and tests | `backend/app/domain/action_*.py`, `backend/app/actions/`, `backend/app/api/v1/technical_debts.py`, and `frontend/app/components/technicalDebt/` |
| Add a new Executor or Verifier | Narrow application-owned protocol plus infrastructure adapter and composition | `backend/app/actions/github_issue_executor.py`, `github_issue_verifier.py`, corresponding `backend/app/infrastructure/` adapters, and `backend/app/api/dependencies.py` |
| Change the database model | Domain invariant, SQLAlchemy model, Alembic revision, persistence/read model, and tests | [Migrations, Seeding and Data Model Extension](../03-data-and-database/migrations-seeding-and-extension.md) |
| Add a frontend capability | Backend response/command contract, frontend wire type and API composable, presentation mapping, page/component, and Vitest coverage | `backend/app/api/v1/`, `frontend/app/types/`, `frontend/app/composables/`, `frontend/app/utils/`, `frontend/app/pages/`, and `frontend/tests/unit/` |

### Add a New Signal Source

Use this path when the source produces canonical observations:

```text
Source
  -> scanner, loader, or read Connector
  -> validated source observation
  -> deterministic normalization
  -> Signal plus Evidence and provenance
  -> persistence and explicit registration/composition
  -> tests
```

The formal Connector registry currently covers Dependency Lifecycle and GitHub Issues;
Semgrep and Git use scanners, while incidents use a database loader. Do not force an
existing ingestion shape into the registry without a source-boundary reason. A
Connector registration alone neither runs ingestion nor proves source health.

### Add a New Agent Tool

Define strict input and result models, implement a narrow capability through
`CandidateInvestigationReader` or another explicit port, and compose a
`ToolRegistration` with truthful effect, risk, and required scopes. Add it to
`build_candidate_tool_registry`; an unregistered tool is never executable.

Keep Candidate scope server-owned and preserve the runtime's schema validation,
policy decision, budgets, safe trace, and grounding rules. Human Validation and
external mutation must not become investigation tools.

### Add a New AI Provider

Implement `InvestigationProvider.next_step` and translate provider-specific data into
the existing `ProviderStep` and `StructuredAssessment` contracts. Add server-owned
selection in `backend/app/agent/provider_composition.py` and validated settings in
`backend/app/core/config.py`.

Preserve bounded tool calls, JSON-safe context, timeouts, strict output validation,
reference validation, safe failures, and the rule that the client cannot select a
provider or model. The current baseline has deterministic and OpenAI providers; it
does not have dynamic provider discovery or fallback routing.

### Add a New Governed Action

Follow the full authority chain:

```text
Action type and immutable proposal
  -> exact-payload human approval
  -> deterministic policy decision
  -> durable execution claim
  -> dedicated Executor
  -> independent verification or reconciliation
  -> API, frontend and audit presentation
  -> tests
```

The current implementation supports only `CREATE_GITHUB_ISSUE`. A new action usually
affects domain types, SQLAlchemy models, an Alembic revision, persistence/read models,
policy rules, executor and verifier contracts, FastAPI schemas/routes, frontend wire
types and mappings, workflow components, and tests. Do not infer permission from an
AI recommendation or a Human Validation decision.

### Add a New Executor

External writes must remain behind a narrow protocol under `backend/app/actions/`,
with the vendor adapter under `backend/app/infrastructure/`. Configuration and
credentials remain server-owned. Policy must allow the exact persisted proposal
before the executor is called, and a separate read-only verifier must establish the
external result. A read Connector is never reused as the writer.

### Change the Database Model

Start with the domain requirement, then update the SQLAlchemy mapping, add an Alembic
revision, update persistence and read models, and test both mapping and MSSQL behavior.
Do not use a storage column as a shortcut that collapses Signal, Candidate, Human
Decision, TechnicalDebt, approval, policy, execution, or verification concepts.

### Add a Frontend Capability

Begin with an implemented backend contract. Add or update the matching `*Api.ts` wire
type and composable, map it into presentation types where useful, build the page or
component, and cover loading, empty, error, and successful states in Vitest.

Frontend utilities may format or organize backend data. They must not recreate
correlation, lifecycle transitions, actor authority, action policy, or external
verification in the browser.

## Change Impact Checklist

When extending the system, check whether the change affects:

- [ ] domain model and invariants
- [ ] persistence mapping and read models
- [ ] Alembic migration or controlled seed
- [ ] API request and response contracts
- [ ] frontend wire types, mapping, and display states
- [ ] Evidence and provenance
- [ ] tool or action policy
- [ ] audit records and relationships
- [ ] unit, API, frontend, database, or external-boundary tests
- [ ] current documentation

## Related Documentation

- [Repository Structure](repository-structure.md)
- [Local Development](local-development.md)
- [Extension Architecture](../02-architecture/extension-architecture.md)
- [Adding a New Connector](../04-signals-context-and-integrations/adding-a-new-connector.md)
- [Migrations, Seeding and Data Model Extension](../03-data-and-database/migrations-seeding-and-extension.md)
