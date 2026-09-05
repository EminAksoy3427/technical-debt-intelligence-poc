# ADR 0001: Option B — Extensible Modular Monolith

Date: 4 September 2026

Status: Accepted as target direction; implementation is incremental.

## Context

The current PoC is a layered modular monolith: deterministic source ingestion,
canonical Signal/Evidence, Candidate correlation, MSSQL persistence, FastAPI
read APIs and Nuxt Candidate Pool/Detail. Source adapters offer useful seams,
but there are no explicit extension contracts, registries or agent runtime.
The Candidate API directly uses the infrastructure read model.

The next steps must accommodate additional sources and later governed agent
capabilities while preserving evidence traceability and human decisions.
Signal, Candidate and TechnicalDebt must remain separate concepts.

## Decision

Adopt **Option B: Extensible Modular Monolith + Ports & Adapters + Explicit
Extension Contracts + Governed Agent Runtime + Async-ready seams**, retaining
**MSSQL/Alembic as the System of Record**.

Preserve a stable conceptual core of Signal, Evidence, Candidate, enterprise
context, deterministic correlation and governance semantics, adding a future
TechnicalDebt lifecycle only through a dedicated slice. Keep acquisition,
provider details, storage, delivery and registry wiring outside that core.

Extract minimal Connector/Normalizer contracts with a concrete connector slice.
Future agent/tool/policy contracts will be introduced **only when their vertical
slices are implemented**. Knowledge-provider boundaries follow concrete needs.
The [overview](../architecture/overview.md) defines the target dependency direction
and explicitly records the current exceptions.

## Rationale

- **Why Option B:** it supports replaceable sources and later capabilities while
  retaining stable domain semantics and evidence identity.
- **Why keep the modular monolith:** one application boundary keeps changes,
  debugging and persistence coordination manageable at PoC scope.
- **Why explicit extension contracts:** integrations should depend on small,
  canonical boundaries instead of leaking provider formats into Candidates.
- **Why not microservices now:** no current slice demonstrates a need for
  independent service deployment; network boundaries would add coordination work.
- **Why not Kafka now:** current flows are deterministic and synchronous; no
  demonstrated event-streaming requirement justifies a broker. Preserve seams
  for later asynchronous execution without choosing transport now.
- **Why not a runtime plugin marketplace now:** simple composition meets the
  next connector need; dynamic discovery, loading and distribution are deferred.
- **Why vertical slices:** each contract should have a concrete caller,
  implementation and verifiable behavior before broader abstractions are added.

## Consequences

Current features continue working while boundaries evolve in small changes.
Some direct dependencies remain temporarily visible. Contracts and adapters add
maintenance cost, so introduce them only where an implemented slice needs them.
No new production topology, executable policy system or agent capability is
claimed by this decision.

Future L4 execution must follow agent preparation, human approval, policy checks,
executor execution, result verification and persisted audit. Assessment is not
authorization, and verification is not closure. This flow is not implemented.

## Known gaps

The remaining non-blocking baseline gaps are direct API-to-infrastructure reads,
infrastructure DTO mapping in `candidate_schemas`, and incident-specific
recurrence logic in correlation. Explicit connector, SourceObservation,
functional normalizer, and Connector Registry contracts now exist for registered
sources. Agent Runtime, Tool Registry, Policy, and an async backbone remain
future work. Deferred treatment of the remaining gaps is recorded in the
[overview](../architecture/overview.md).

A missing `candidate_models` import in Alembic metadata assembly was identified
during the 4 September architecture baseline and resolved during the same
re-baseline. Candidate ORM tables are now included in Alembic target metadata;
no schema change and no migration revision were required.

This ADR authorizes no code or schema fixes in Package 2.

## Deferred decisions

Exact contract signatures and placement, registry composition details, agent
runtime/tool/provider choices, policy evaluation and approval implementation,
Knowledge provider behavior, async transport, TechnicalDebt lifecycle/storage,
and future navigation are deferred to their respective vertical slices.
Service extraction or a runtime marketplace requires new evidence and a later
decision. This package changes documentation only.
