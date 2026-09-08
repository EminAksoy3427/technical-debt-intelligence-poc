# Module Boundaries

## Why Module Boundaries Matter

A modular monolith shares a runtime and database, so directory names alone do not
prevent accidental coupling. Explicit ownership keeps source observations, canonical
facts, AI recommendations, human decisions, policy authorization, external mutation,
and verification from collapsing into one undifferentiated workflow.

## Backend Boundaries

| Module / Area | Responsibility | Important Code Locations |
|---|---|---|
| Domain model | Defines validated domain values and lifecycle records. | `backend/app/domain/` |
| Signal normalization | Produces a `NormalizedSignal` with matching Signal and Evidence identities for supported sources. | `backend/app/signal_ingestion.py`, `backend/app/semgrep_ingestion.py`, `backend/app/git_history_ingestion.py`, `backend/app/incident_ingestion.py`, `backend/app/dependency_lifecycle_ingestion.py` |
| Candidate correlation | Groups canonical Signals deterministically by asset and problem family, including the recurring-incident threshold. | `backend/app/candidate_correlation.py` |
| Connector boundary | Describes and registers read-only acquisition callables; the current registry contains dependency-lifecycle and GitHub Issues connectors. | `backend/app/connectors/contracts.py`, `backend/app/connectors/registry.py`, `backend/app/connectors/` |
| Enterprise and dependency context | Reads persisted assets, ownership, relationships, incidents, and bounded dependency reachability for Candidate views and tools. | `backend/app/infrastructure/database/candidate_enterprise_context.py`, `backend/app/infrastructure/database/candidate_dependency_context.py`, `backend/app/infrastructure/database/candidate_investigation_reader.py` |
| Agent investigation | Owns provider and tool contracts, the explicit tool registry, authorization policy, bounded runtime, and structured audit contracts. | `backend/app/agent/`, `backend/app/infrastructure/database/candidate_agent_runtime.py` |
| Human governance | Validates commands, enforces legal Candidate transitions, records decisions, and creates TechnicalDebt only for `VALIDATE`. | `backend/app/governance/` |
| Governed actions | Prepares immutable proposals, binds human approval to a fingerprint, evaluates policy, invokes the writer, and verifies or reconciles the result. | `backend/app/actions/` |
| Persistence | Maps domain records to SQLAlchemy models, implements repositories and read models, and creates the MSSQL engine. | `backend/app/infrastructure/database/`, `backend/alembic/` |
| External adapters | Implements scanners, controlled loaders, GitHub acquisition, GitHub execution, and GitHub verification. | `backend/app/infrastructure/` |
| API delivery | Exposes health, Candidate, agent-run, human-decision, TechnicalDebt action, and connector-inventory endpoints. | `backend/app/api/v1/`, `backend/app/api/dependencies.py`, `backend/app/main.py` |
| Configuration | Validates server-owned settings for database access, CORS, providers, governance, targets, limits, and credentials. | `backend/app/core/config.py` |

These are capability boundaries, not independently deployable services. The current
use-case modules directly use selected persistence functions and SQLAlchemy sessions,
so the codebase does not claim complete persistence inversion.

## Frontend Boundary

`frontend/app` is a Nuxt governance workspace. Pages organize overview, source,
Candidate, and TechnicalDebt workflows; components present those workflows; and
composables in `frontend/app/composables` call the FastAPI endpoints using wire types
from `frontend/app/types`.

Utilities map API responses, derive display state, and prepare client requests. They
support presentation and interaction but do not grant human authority, evaluate
backend execution policy, create TechnicalDebt, or mutate GitHub directly. The
backend remains authoritative even when the UI hides or enables an action.

## Boundary Rules

- A Signal is a canonical observation; it is not TechnicalDebt.
- Candidate correlation is deterministic and does not perform human validation.
- External acquisition belongs in scanners, loaders, or read-only Connector
  registrations; it does not imply write authority.
- Provider-specific AI access stays behind `InvestigationProvider`.
- Agent tools are explicitly registered, typed, candidate-scoped, and currently
  read-only.
- Human validation is not an agent tool, and agent modules do not call governance or
  action write services.
- Human approval records consent to an exact proposal; execution policy separately
  determines whether the action is allowed.
- External writes use the dedicated executor protocol; verification uses a separate
  GET-only port.
- Persistence models store state but do not replace domain concepts or controls.
- Frontend behavior cannot override server-owned identity, target, provider, policy,
  or execution configuration.

## Example Request Path

A Candidate detail read follows this implemented path:

```text
Nuxt Candidate page
  -> useCandidateApi composable
  -> GET /api/v1/candidates/{candidate_id}
  -> FastAPI Candidate route
  -> database Candidate read model and governance projection
  -> domain Candidate, Signal, Evidence and context values
  -> Pydantic response contract
  -> frontend mapping and display state
```

The path is read-only. Agent investigation and human validation are separate POST
operations with their own authorization and audit behavior.

## Related Documentation

- [System Architecture](system-architecture.md)
- [Extension Architecture](extension-architecture.md)
- [API Contract](../api-contract.md)
- [System Overview](../01-overview/system-overview.md)
