# Adding a connector

This guide describes the **current** connector architecture. It is an in-code
extension path, not a plugin marketplace, runtime discovery system, or
installable connector catalog.

A **Connector** is responsible for acquiring source-specific observations.

A **Normalizer** is responsible for mapping supported observations into
canonical technical-debt signal semantics.

These are separate responsibilities. Not every connector must immediately have
a Normalizer.

```text
Source
  → Connector
  → SourceObservation
  → optional Normalizer
  → optional NormalizedSignal
```

Reference implementations:

| Role | Connector | Current flow |
| --- | --- | --- |
| Connector + Normalizer | `dependency-lifecycle` | local JSON → `SourceObservation` → Normalizer → `NormalizedSignal` |
| Acquisition-only | `github-issues` | GitHub REST → `GitHubIssueRecord` → `SourceObservation` |

GitHub Issues currently **stops at `SourceObservation`**. It does not produce
Signal, Candidate, or TechnicalDebt. A GitHub Issue is not technical debt by
default.

## Connector vs Normalizer

### Connector

The Connector owns the acquisition boundary:

- works with source-specific record types
- produces `SourceObservation`
- attaches provenance
- does not know Candidate
- does not know TechnicalDebt

Current composition type:

```text
ConnectorRegistration = descriptor + acquire
```

`ConnectorRegistration` does **not** contain a normalizer.

### Normalizer

The Normalizer is a separate function from registration:

- accepts a supported `SourceObservation`
- maps to canonical signal semantics
- returns `NormalizedSignal` (`Signal` + nonempty `Evidence`)
- is not part of `ConnectorRegistration`

`dependency-lifecycle` is the reference for this optional second step.
`normalize_dependency_lifecycle_observation()` lives beside the connector, but
the registry still stores only `descriptor` and `acquire`.

## Source-specific records

Source-specific records remain source-specific. Do not introduce one universal
`ExternalSourceRecord` DTO, and do not flatten every source into a giant shared
schema.

Current examples:

| Record | Source |
| --- | --- |
| `DependencyLifecycleFinding` | local JSON lifecycle export |
| `GitHubIssueRecord` | GitHub Issues REST payload subset |

The connector wraps that record. Canonical meaning is added later, and only if
a Normalizer exists for that source.

## SourceObservation

`SourceObservation` is the stable boundary between acquisition and later
interpretation. Current fields:

| Field | Role |
| --- | --- |
| `provenance` | `SourceObservationRef` identity |
| `observed_at` | timezone-aware source-side event/update time |
| `record` | the source-specific record |

There is no `fetch_time`, `acquisition_time`, `health`, or `checkpoint` field.

`SourceObservation` is not a canonical Signal. Registration is not successful
ingestion. Connector registration is not proof that acquisition ran.

## Provenance

Provenance uses:

```text
SourceObservationRef(
    source_system,
    source_record_id,
)
```

Rules:

- `source_system` is a stable source identifier and should align with
  descriptor `source_system`.
- `source_record_id` is stable identity in the source, not mutable display
  text.

Current examples:

| Connector | `source_system` | `source_record_id` |
| --- | --- | --- |
| dependency-lifecycle | `dependency-lifecycle` | `finding.source_record_id` |
| github-issues | `github-issues` | `str(issue.id)` |

GitHub uses the issue `id`. Do **not** use `issue.title` or `issue.number` as
canonical provenance identity. `number` is a useful display/reference field on
`GitHubIssueRecord`; it is not the provenance key.

## Timestamp

`observed_at` should represent the meaningful source-side event or update time.
It must be timezone-aware. Do not default to `datetime.now()`, and do not add
an acquisition timestamp to the contract.

Current examples:

| Connector | `observed_at` |
| --- | --- |
| dependency-lifecycle | `finding.observed_at` |
| github-issues | `issue.updated_at` |

## Descriptor

`ConnectorDescriptor` fields:

| Field | Meaning |
| --- | --- |
| `connector_id` | stable registry identifier |
| `display_name` | human-readable name |
| `version` | connector version string |
| `source_system` | source identity used with provenance |
| `transport` | how the source is reached |
| `read_only` | whether acquisition is read-only |

Current descriptors:

| `connector_id` | `transport` | `read_only` |
| --- | --- | --- |
| `dependency-lifecycle` | `local-json` | `true` |
| `github-issues` | `https` | `true` |

Descriptor metadata is inventory metadata. It does **not** prove health,
successful ingestion, last run, or connectivity.

**Registered != Healthy.**

## Registration

Registration is explicit, in-code, and deterministic.

A connector must be added to `CONNECTOR_REGISTRY` in
`backend/app/connectors/registry.py`. Current composition:

```text
CONNECTOR_REGISTRY = ConnectorRegistry(
    registrations=(
        DEPENDENCY_LIFECYCLE_CONNECTOR,
        GITHUB_ISSUES_CONNECTOR,
    ),
)
```

This is not:

- dynamic discovery
- `importlib` plugin loading
- entry points
- runtime plugin installation
- a marketplace

Duplicate `connector_id` values are rejected at registry construction
(`ValueError: Duplicate connector identifier: ...`). Registry `list()` preserves
registration order. `get(connector_id)` raises `KeyError` for unknown ids.

## API visibility

Once a connector is explicitly registered, `GET /api/v1/connectors` exposes
descriptor metadata through the registry inventory (`items` and `count`). Each
item currently includes descriptor fields plus `status`.

`status` is always `registered`. That means composition registration.

This endpoint does **not**:

- execute the connector
- check source availability
- call GitHub
- prove health
- prove ingestion success

There is no automatic health reporting, no last-run field, and no run-connector
API.

## Configuration

Connector configuration remains source-specific. Do not invent a universal
`ConnectorConfiguration` model. Configuration should contain only what
acquisition needs.

Current examples:

| Connector | Configuration |
| --- | --- |
| dependency-lifecycle | `Path` to the local JSON source |
| github-issues | repository owner, repository name, request timeout |

GitHub settings currently come from backend environment-backed `Settings`
(`GITHUB_REPOSITORY_OWNER`, `GITHUB_REPOSITORY_NAME`,
`GITHUB_REQUEST_TIMEOUT_SECONDS`). Those values identify a public demo
repository; they are not secrets.

## Security

Current principles:

- credentials stay backend-only
- use `SecretStr` when a credential is introduced
- never expose secrets through Nuxt `runtimeConfig`
- never commit `.env`; commit `.env.example` only
- never use real secrets in tests
- never log `Authorization` or header secrets
- never dump secret-bearing response bodies
- use least privilege
- hard-code a trusted API origin when appropriate
- use an explicit finite timeout for blocking external I/O

GitHub currently hard-codes `https://api.github.com` as the trusted origin.

**The current GitHub READ connector has no token support.** Do not document
GitHub PAT authentication as existing on the acquisition connector. The Day 2
proof uses unauthenticated public READ.

That connector is not the GitHub Issue Executor and not the GitHub Issue
Verifier. Acquisition (`backend/app/connectors/github_issues.py`) remains
GET-only SourceObservation collection. Action-plane write and read-back live
separately under `backend/app/actions` and
`backend/app/infrastructure/github_issue_executor.py` /
`github_issue_verifier.py`. See the
[architecture overview](../architecture/overview.md).

## Timeout, retry, and errors

A finite timeout is required where external blocking I/O exists.

| Connector | Timeout |
| --- | --- |
| github-issues HTTP | configured 5 second timeout |
| dependency-lifecycle local JSON | no transport timeout is needed for the pure local-file reference flow |

Use source-local typed errors rather than a giant enterprise-global exception
tree.

Current GitHub errors:

- `GitHubIssuesSourceError`
- `GitHubIssuesConfigurationError`
- `GitHubIssuesTransportError`
- `GitHubIssuesApiError`
- `GitHubIssuesResponseFormatError`

Current dependency-lifecycle errors:

- `DependencyLifecycleSourceError`
- `DependencyLifecycleSourceFormatError`

Retry is source-specific and should not be introduced generically without a
real requirement. The current GitHub connector has no retry framework.

Semgrep remains a legacy scanner path. Its `subprocess.run(...)` call currently
has no explicit timeout; that gap is deferred and is not part of the Connector
contract.

## Testing

The default deterministic suite must **not** depend on Internet access.

| Layer | When | What to cover |
| --- | --- | --- |
| UNIT | always for a new connector | acquisition mapping, `SourceObservation` creation, provenance, timestamp semantics, error mapping, timeout where relevant, no secret leakage, read-only behavior where applicable |
| REGISTRY | always when registering | registration, deterministic ordering if changed, duplicate ID rejection |
| NORMALIZATION | only when the source produces canonical Signal now | mapping to `NormalizedSignal` / Signal + Evidence |
| PERSISTENCE | only when the normalized path writes existing Signal/Evidence persistence | existing persistence contracts |
| EXTERNAL | only where a safe live external proof exists | separately marked `@pytest.mark.external` |

GitHub external proof is separately marked `external`. It is not part of
`python -m pytest -m "not integration and not external"`.

MSSQL tests remain `@pytest.mark.integration` and are also excluded from the
deterministic suite.

## Database impact

Every connector implementation must make an explicit database-impact decision.

**Default: NO SCHEMA CHANGE.**

Do not create connector tables merely because a connector exists. Database
persistence is justified only when an actual system-of-record requirement
exists.

Registry inventory currently remains in code. Day 2 Packages 2–4 added no
connector, health, run, or checkpoint tables. That was deliberate.

See [database evolution and migrations](../database/evolution-and-migrations.md).

## Current extension workflow

1. Keep the source record type source-specific.
2. Implement acquisition that returns `tuple[SourceObservation[...], ...]`.
3. Attach `SourceObservationRef` using a stable `source_system` and
   `source_record_id`.
4. Set timezone-aware `observed_at` from the source-side event/update time.
5. Publish a truthful `ConnectorDescriptor`.
6. Register `ConnectorRegistration(descriptor=..., acquire=...)`.
7. Add that registration to `CONNECTOR_REGISTRY`.
8. Keep configuration source-specific and backend-only.
9. Add source-local errors and a timeout for blocking external I/O.
10. Record the database-impact decision. Default is no schema change.
11. Add unit and registry tests. Add normalization/persistence/external tests
    only when those paths exist.
12. Confirm `GET /api/v1/connectors` shows the new descriptor.
13. Update this guide if the actual architecture changed.

Optional: add a Normalizer only when this source should produce canonical
Signal + Evidence now.

## Definition of done

A future connector is done when all of the following are true:

- truthful `ConnectorDescriptor`
- acquisition boundary
- source-specific record
- `SourceObservation`
- stable provenance
- timezone-aware `observed_at`
- source-local error strategy
- timeout for blocking external I/O
- secure config handling
- explicit registry registration
- unit tests
- registry tests
- optional normalization tests
- optional persistence tests
- optional external proof
- API inventory visibility verified
- DB impact decision recorded
- docs updated
- `git diff --check`

Normalization is **not** mandatory for acquisition-only connectors.
GitHub Issues is the current acquisition-only reference.
