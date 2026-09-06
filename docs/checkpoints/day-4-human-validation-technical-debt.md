# Day 4 acceptance checkpoint — Human Validation and TechnicalDebt

Baseline before this documentation package: **49e47ce**
(`49e47ce06693f27996eea905df6bf42ded994124`).

This checkpoint records Day 4 implementation through frontend. It adds no
product capability.

## A. Baseline / final implementation commit

| Check | Value |
| --- | --- |
| Branch | `main` |
| Implementation HEAD | `49e47ce` — `feat: add human validation and technical debt frontend` |
| `origin/main` | `49e47ce` |
| Working tree before docs | clean |

Day 4 implementation commits:

```text
ab9a9f4 feat: add human validation governance contracts
fe84624 feat: persist atomic human validation lifecycle
fcae500 feat: expose human validation and technical debt APIs
49e47ce feat: add human validation and technical debt frontend
```

## B. Day 4 implemented capabilities

- HumanDecision domain (`VALIDATE`, `REJECT`, `REQUEST_INFO`)
- Candidate governance derivation and revision from HumanDecision history
- TechnicalDebt domain (`lifecycle_status=REGISTERED` only)
- Persistence + Alembic `20260906_01`
- Atomic Human Validation application service
- MSSQL same-Candidate governance locking (`UPDLOCK`, `HOLDLOCK`) plus uniqueness
- Human Validation API
- Candidate Detail governance projection
- TechnicalDebt list/detail API
- Human Validation frontend
- TechnicalDebt portfolio/detail frontend

`MERGE` is not implemented.

## C. Acceptance evidence

These are package-stage results. They were not re-run as one combined Day 4
suite for this documentation package.

| Stage | Recorded result |
| --- | --- |
| Package 3 focused | **143 passed** |
| Package 3 MSSQL/migration | **3 passed** at that stage (`test_mssql_governance_persistence.py` + estate migration) |
| Package 3 transaction-ownership mini-fix | focused governance suite plus MSSQL governance persistence, including the two-session same-revision VALIDATE proof |
| Package 4 API regression | **210 passed** |
| Package 4 broad deterministic | **552 passed**, 17 deselected; remaining failures were Semgrep-executable-absent (`SemgrepExecutableNotFoundError`) |
| Package 5 frontend final | **28 test files**, **191 passed**; typecheck passed; build passed |

The Package 4 written report stated that MSSQL integration tests were not
re-run in that API package. The lock mechanism applies to same-Candidate
governance commands. The two current MSSQL governance proofs live in
`backend/tests/integration/test_mssql_governance_persistence.py`:

- schema/head `20260906_01`, FKs, and uniqueness
- two-session integration proof of concurrent same-revision `VALIDATE`: one
  winner, loser observes stale revision/conflict, one decision #1, exactly one
  TechnicalDebt

SQLite tests do not prove MSSQL concurrency.

Live frontend proof (Package 5, one synthetic local Candidate):

```text
Candidate Human Validation
  → VALIDATE
  → persisted refresh
  → REGISTERED TechnicalDebt
  → /technical-debts portfolio
  → /technical-debts/{id} detail
  → Candidate backlink
```

## D. Authority boundaries

| Boundary | Status |
| --- | --- |
| No Agent Tool for Human Validation | **PASS** |
| No GitHub write | **PASS** |
| No L4 execution | **PASS** |
| No risk / effort / owner invention | **PASS** |
| Client cannot submit actor, role, approval, or authorization | **PASS** |
| Human actor is PoC server configuration only | **PASS** — not enterprise authentication |

## E. Known limitations

- Human actor is `HUMAN_GOVERNANCE_ENABLED` + `HUMAN_GOVERNANCE_ACTOR_REFERENCE`
  only. There is no OAuth, ADFS, SSO, JWT enterprise identity, or reviewer RBAC.
- Local Semgrep executable may be absent.
- Local `.env` may select the OpenAI investigation provider.
- One synthetic local Candidate was validated during live proof.
- No L3 ActionProposal.
- No L4 execution, verification, or closure.

## F. Day 5 boundary / next work

Do not implement this in Day 4.

Next planned direction is **ActionProposal / L3 preparation**. That work is
outside the current Human Validation / REGISTERED TechnicalDebt slice.

## Acceptance checklist

| Item | Result |
| --- | --- |
| Candidate remains distinct from TechnicalDebt | **PASS** |
| HumanDecision is separate from Agent assessment | **PASS** |
| VALIDATE creates exactly one TechnicalDebt | **PASS** |
| REJECT creates none | **PASS** |
| REQUEST_INFO creates none | **PASS** |
| Human Validation transaction is atomic | **PASS** |
| concurrent same-revision VALIDATE protected on MSSQL | **PASS** |
| client cannot manufacture actor/approval | **PASS** |
| Candidate refresh restores governance | **PASS** |
| TechnicalDebt list/detail exist | **PASS** |
| frontend respects stale revision | **PASS** |
| no Agent Tool performs Human Validation | **PASS** |
| no GitHub write exists | **PASS** |
| ActionProposal / L3 preparation | **DEFERRED** |
| L4 approval/execution | **DEFERRED** |
| verification / closure | **DEFERRED** |
| enterprise authentication / reviewer RBAC | **DEFERRED** |

See current-state detail in the
[architecture overview](../architecture/overview.md),
[API contract](../api-contract.md),
[database evolution](../database/evolution-and-migrations.md), and
[domain invariants](../domain/invariants.md).
