# Documentation Guide

This documentation set explains the Technical Debt Intelligence & Governance proof of concept as it exists in the repository today.

It is organized around the system architecture and operating model, not around the order in which the work was built. The intended audience is developers, architects, technical leads, and future project owners.

For a product-level introduction, start with the [root README](../README.md). This guide maps the rest of the documentation.

## Recommended Reading Path

If you have not seen the project before, read these documents in order:

1. [../README.md](../README.md)
2. [01-overview/system-overview.md](01-overview/system-overview.md)
3. [01-overview/end-to-end-flow.md](01-overview/end-to-end-flow.md)
4. [01-overview/core-concepts.md](01-overview/core-concepts.md)
5. [02-architecture/system-architecture.md](02-architecture/system-architecture.md)
6. [03-data-and-database/database-overview.md](03-data-and-database/database-overview.md)
7. [07-handover-and-roadmap/handover-guide.md](07-handover-and-roadmap/handover-guide.md)

After this path, a new reader should understand what the system does, how information moves through it, the main domain concepts, the overall architecture, where persistent data lives, and how to continue development.

## Documentation Areas

### 01 - Overview

Answers: **What is this system and how does it work?**

| File | Purpose |
|---|---|
| [system-overview.md](01-overview/system-overview.md) | Describes the platform purpose, operating model, and current PoC scope. |
| [end-to-end-flow.md](01-overview/end-to-end-flow.md) | Walks through the path from source observation to governed action and audit. |
| [core-concepts.md](01-overview/core-concepts.md) | Defines Signal, Evidence, Candidate, Technical Debt, and related terms. |
| [implementation-status.md](01-overview/implementation-status.md) | States what the current repository actually implements. |

### 02 - Architecture

Answers: **How is the system designed and why?**

| File | Purpose |
|---|---|
| [system-architecture.md](02-architecture/system-architecture.md) | Explains the extensible modular monolith and major runtime components. |
| [module-boundaries.md](02-architecture/module-boundaries.md) | Describes the internal boundaries between domain, API, persistence, agent, and integrations. |
| [extension-architecture.md](02-architecture/extension-architecture.md) | Shows how connectors, tools, providers, policies, and executors are isolated behind contracts. |
| [security-and-trust-boundaries.md](02-architecture/security-and-trust-boundaries.md) | Identifies trust boundaries between the core, AI runtime, humans, and external systems. |
| [architecture-decisions.md](02-architecture/architecture-decisions.md) | Records the design choices that still govern the current implementation. |

### 03 - Data and Database

Answers: **What data does the system store, how is it related, and how does persistence work?**

This area is written for application developers, not only for database specialists. Start with the overview if you need the persistence model explained in system terms before looking at schema details.

Microsoft SQL Server is the persistent system of record. SQLAlchemy maps application objects to that store. Alembic manages schema evolution.

| File | Purpose |
|---|---|
| [database-overview.md](03-data-and-database/database-overview.md) | Introduces where data lives and how persistence supports the lifecycle. |
| [conceptual-data-model.md](03-data-and-database/conceptual-data-model.md) | Explains the main entities and how they relate, without requiring SQL expertise. |
| [database-schema-and-persistence.md](03-data-and-database/database-schema-and-persistence.md) | Maps conceptual entities to the current schema and persistence code. |
| [data-lifecycle.md](03-data-and-database/data-lifecycle.md) | Shows how records move from signals and evidence through decisions, actions, and audit. |
| [migrations-seeding-and-extension.md](03-data-and-database/migrations-seeding-and-extension.md) | Explains schema changes, seed data, and how to extend persistence safely. |

### 04 - Signals, Context and Integrations

Answers: **Where does technical-debt information come from and how does it become a candidate?**

A signal is not technical debt. Observations enter through connectors, are normalized, and only become candidates after evidence, provenance, and enterprise context are attached.

```text
External Source
      ↓
Connector / Ingestion
      ↓
Normalized Signal
      ↓
Evidence & Provenance
      ↓
Enterprise Context
      ↓
Candidate
```

| File | Purpose |
|---|---|
| [signal-ingestion-and-normalization.md](04-signals-context-and-integrations/signal-ingestion-and-normalization.md) | Describes how source observations become canonical signals. |
| [evidence-provenance-and-correlation.md](04-signals-context-and-integrations/evidence-provenance-and-correlation.md) | Explains supporting evidence, origin tracking, and candidate correlation. |
| [enterprise-context.md](04-signals-context-and-integrations/enterprise-context.md) | Describes the controlled asset, ownership, relationship, and incident model. |
| [connector-architecture.md](04-signals-context-and-integrations/connector-architecture.md) | Explains connector contracts and how external sources are isolated from the core. |
| [adding-a-new-connector.md](04-signals-context-and-integrations/adding-a-new-connector.md) | Shows how to add a new source integration using the existing contracts. |

### 05 - Agent and Governance

Answers: **How does AI assist the process, and how are decisions and external actions controlled?**

AI investigates and recommends. It does not validate technical debt, approve actions, or write to external systems.

Keep these distinctions:

```text
AI Recommendation   ≠ Human Decision
Human Approval      ≠ Policy Authorization
Connector           ≠ Executor
Execution Request   ≠ Verified Execution
```

Responsibility chain:

```text
Deterministic Core  →  establishes facts and state
AI Agent            →  investigates and recommends
Human               →  makes authoritative governance decisions
Policy              →  controls whether an action is allowed
Executor            →  performs an approved external action
Verification        →  confirms the real-world result
Audit               →  preserves traceability
```

| File | Purpose |
|---|---|
| [agent-overview.md](05-agent-and-governance/agent-overview.md) | Describes the governed investigation role and its limits. |
| [investigation-runtime-and-tools.md](05-agent-and-governance/investigation-runtime-and-tools.md) | Explains bounded runtime controls and registered read tools. |
| [provider-and-grounding.md](05-agent-and-governance/provider-and-grounding.md) | Covers the provider boundary, grounding, and structured assessments. |
| [human-validation-and-lifecycle.md](05-agent-and-governance/human-validation-and-lifecycle.md) | Documents human decisions that move a candidate into governed technical debt. |
| [policy-actions-execution-and-audit.md](05-agent-and-governance/policy-actions-execution-and-audit.md) | Covers action proposals, approval, policy, execution, verification, and audit. |

### 06 - API, Frontend and Development

Answers: **How do I run, understand, modify, test, and extend the application?**

This area is practical. Use it when you need to work in `backend/`, `frontend/`, or the supporting test and source fixtures.

| File | Purpose |
|---|---|
| [api-and-frontend-overview.md](06-api-frontend-and-development/api-and-frontend-overview.md) | Describes the FastAPI surface and the Nuxt governance workspace. |
| [user-flow.md](06-api-frontend-and-development/user-flow.md) | Maps the operator path through overview, candidates, validation, and actions. |
| [repository-structure.md](06-api-frontend-and-development/repository-structure.md) | Explains the main repository directories and where to look first. |
| [local-development.md](06-api-frontend-and-development/local-development.md) | Covers local setup, configuration, and running the application. |
| [testing-and-troubleshooting.md](06-api-frontend-and-development/testing-and-troubleshooting.md) | Points to the test suites and common local failure modes. |
| [extending-the-system.md](06-api-frontend-and-development/extending-the-system.md) | Summarizes how to add behavior without breaking existing boundaries. |

### 07 - Handover and Roadmap

Answers: **What should a new owner know, what is still PoC-specific, and how can the platform evolve?**

Keep these four things distinct:

- **Current implemented PoC capabilities** — what the repository actually supports.
- **PoC-specific controlled assumptions** — bounded data, reference integrations, and demonstration constraints.
- **Production readiness gaps** — work still required before enterprise production use.
- **Future development** — possible evolution, not current functionality.

| File | Purpose |
|---|---|
| [handover-guide.md](07-handover-and-roadmap/handover-guide.md) | Gives a new owner the operating picture and the safest next steps. |
| [production-readiness.md](07-handover-and-roadmap/production-readiness.md) | Separates current PoC limits from production adoption requirements. |
| [future-development.md](07-handover-and-roadmap/future-development.md) | Describes possible evolution without treating it as implemented work. |

## Reading by Role

**New Developer**
[Root README](../README.md) → [System Overview](01-overview/system-overview.md) → [System Architecture](02-architecture/system-architecture.md) → [Database Overview](03-data-and-database/database-overview.md) → [Local Development](06-api-frontend-and-development/local-development.md)

**Architect / Technical Lead**
[System Overview](01-overview/system-overview.md) → [System Architecture](02-architecture/system-architecture.md) → [Module Boundaries](02-architecture/module-boundaries.md) → [Architecture Decisions](02-architecture/architecture-decisions.md) → [Production Readiness](07-handover-and-roadmap/production-readiness.md)

**Integration Developer**
[Signal Ingestion](04-signals-context-and-integrations/signal-ingestion-and-normalization.md) → [Connector Architecture](04-signals-context-and-integrations/connector-architecture.md) → [Adding a New Connector](04-signals-context-and-integrations/adding-a-new-connector.md) → [Policy, Actions, Execution and Audit](05-agent-and-governance/policy-actions-execution-and-audit.md)

**AI / Agent Developer**
[Agent Overview](05-agent-and-governance/agent-overview.md) → [Investigation Runtime and Tools](05-agent-and-governance/investigation-runtime-and-tools.md) → [Provider and Grounding](05-agent-and-governance/provider-and-grounding.md) → [Human Validation](05-agent-and-governance/human-validation-and-lifecycle.md)

**Project Owner**
[Root README](../README.md) → [System Overview](01-overview/system-overview.md) → [Implementation Status](01-overview/implementation-status.md) → [Handover Guide](07-handover-and-roadmap/handover-guide.md) → [Future Development](07-handover-and-roadmap/future-development.md)

## Documentation Principles

- Explain purpose before implementation detail.
- Prefer system concepts over historical project milestones.
- Keep current implementation separate from future development.
- Do not claim unsupported capabilities.
- Preserve evidence and provenance terminology.
- Keep AI, human decision, policy authorization, execution, and verification separate.
- Use real repository paths when referring to code.
- Prefer short diagrams, tables, and examples over long prose.
- Avoid unnecessary duplication between documents.

## Source of Truth

When documents appear to conflict, use this order:

1. **Current implementation and automated tests** — the running code and tests in this repository.
2. **Current primary documentation** — this documentation set, describing the system as it exists now.
3. **Architecture decisions** — recorded choices that still apply to the current design.
4. **Future development documents** — possible evolution, never treated as implemented behavior.

Historical plans are not a source of truth for the current system.
