# Architecture Decisions

These decisions are visible in the Current PoC Baseline and continue to constrain
development. They are not a historical ADR log.

## Decision: Use an extensible modular monolith

**Decision**

Keep the backend in one FastAPI application while separating capabilities into
explicit modules and external adapters.

**Why**

The current scope needs strong responsibility boundaries, not independent deployment
or distributed coordination.

**Trade-off**

Modules share a runtime and database, so dependency discipline is enforced by code
structure and tests rather than service isolation.

**Consequence**

New capabilities should extend existing contracts and composition points before any
separate service is considered.

## Decision: Establish facts deterministically before AI reasoning

**Decision**

Use source-specific validation, canonical normalization, stable identities, and
deterministic Candidate correlation before agent investigation.

**Why**

Source observations require reproducible provenance and meaning before they can
support review.

**Trade-off**

Each supported source needs explicit mapping, and heuristics remain intentionally
conservative.

**Consequence**

AI output may interpret available facts but must not replace ingestion, correlation,
or stored system state.

## Decision: Keep authoritative technical-debt decisions human-controlled

**Decision**

Only the human-validation use case can create TechnicalDebt, and only a `VALIDATE`
decision does so.

**Why**

A Candidate and an AI recommendation are insufficient authority for a governed
technical-debt record.

**Trade-off**

The workflow requires explicit review and may not progress automatically.

**Consequence**

Agent modules and tools must remain unable to invoke governance write services.

## Decision: Isolate external reads behind acquisition boundaries

**Decision**

Represent source access with scanners, validated loaders, and explicitly registered
read-only Connectors.

**Why**

Source-specific transport and records should not leak into Candidate or governance
meaning.

**Trade-off**

The baseline has more than one acquisition shape, and not every Connector currently
has a Signal normalizer.

**Consequence**

A new source must preserve provenance and, if it feeds Signals, add an explicit
canonical mapping rather than writing domain records from raw payloads.

## Decision: Separate external writers from Connectors

**Decision**

Perform GitHub mutation through a dedicated executor protocol, not through the
read-only Connector registry or agent tools.

**Why**

Read access must not silently acquire mutation authority.

**Trade-off**

Read and write integrations for the same external platform require separate contracts
and configuration.

**Consequence**

Every future external mutation requires its own narrow executor boundary and governed
action path.

## Decision: Enforce policy after approval and before execution

**Decision**

Evaluate deterministic execution policy from persisted and server-owned inputs
immediately before an external action is claimed.

**Why**

Human approval confirms intent but does not prove that the action type, exact payload,
target, feature state, or executor is authorized and ready.

**Trade-off**

An approved proposal can still be denied.

**Consequence**

Approval and authorization remain separate persisted concepts, and executors do not
make policy decisions.

## Decision: Verify external effects separately

**Decision**

Read GitHub back through a dedicated verifier and compare it with the approved
proposal after execution.

**Why**

An execution request, response, or stored external reference does not establish the
final external state.

**Trade-off**

Verification adds another external call and can return unavailable or failed even
after successful execution.

**Consequence**

Code and UI must distinguish execution status from verification status and preserve
reconciliation for uncertain outcomes.

## Decision: Put AI providers behind an application-owned port

**Decision**

Make the runtime depend on `InvestigationProvider`, with provider selection controlled
by server settings.

**Why**

The investigation loop, tool policy, audit, and assessment contract should not depend
on a specific SDK or model.

**Trade-off**

Provider adapters must translate between provider responses and strict runtime
contracts.

**Consequence**

Provider replacement must preserve bounded steps, structured output, reference
validation, timeouts, and server-owned configuration.

## Decision: Use MSSQL as the PoC system of record

**Decision**

Persist enterprise context, Signals, Evidence, Candidates, agent audit, human
decisions, TechnicalDebt, and governed actions in Microsoft SQL Server through
SQLAlchemy and Alembic.

**Why**

The governance workflow needs relational integrity, durable audit records, explicit
transactions, locking, and versioned schema evolution.

**Trade-off**

Runtime database operations require an `mssql+pyodbc` configuration, and several
application services are directly coupled to SQLAlchemy persistence functions.

**Consequence**

Schema changes use Alembic, persistence mappings remain separate from domain types,
and database integration tests stay opt-in when MSSQL is unavailable.

## Decision: Isolate evaluation ground truth from runtime decisions

**Decision**

Keep controlled correlation expectations under `evaluation/ground_truth` and prevent
runtime modules, migrations, or seed logic from importing them.

**Why**

Evaluation answers must measure behavior rather than supply answers to the running
system.

**Trade-off**

Evaluation fixtures require separate maintenance and validation against controlled
source facts.

**Consequence**

Ground-truth data cannot become an application shortcut, database table, or agent
context source.

## Decision: Keep domain authority in the backend

**Decision**

Use the Nuxt frontend as an API client and governance workspace while keeping domain
transitions, actor attribution, policy, execution targets, and credentials in the
backend.

**Why**

Browser state and presentation logic cannot be trusted to enforce authoritative
governance or external-write controls.

**Trade-off**

Frontend and backend wire types and display mappings must evolve together.

**Consequence**

UI affordances may guide users, but every authoritative operation must be validated
and enforced by the FastAPI application.

## Related Documentation

- [System Architecture](system-architecture.md)
- [Module Boundaries](module-boundaries.md)
- [Extension Architecture](extension-architecture.md)
- [Security and Trust Boundaries](security-and-trust-boundaries.md)

