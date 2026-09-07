import ast
import inspect
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.orm import Session

from app.actions.approval import approve_action_proposal
from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalAlreadyApproved,
    ActionProposalNotFound,
    ApproveActionProposalCommand,
    CompetingActionApprovalExists,
    PrepareActionProposalCommand,
    StaleActionProposalFingerprint,
    TechnicalDebtNotFound,
)
from app.actions.preparation import prepare_action_proposal
from app.domain.action_approvals import ActionApproval
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_approval_persistence import load_action_approval
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import load_action_proposal
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_persistence import (
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_persistence import (
    persist_technical_debt,
)

CREATED_AT = datetime(2026, 9, 7, 18, 30, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_A_ID = UUID("00000000-0000-0000-0000-000000000501")
PROPOSAL_B_ID = UUID("00000000-0000-0000-0000-000000000502")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")
ACTOR = HumanActorContext(actor_reference="poc:local-reviewer")
PREPARATION = ActionPreparationContext(
    target_repository_owner="tdi-demo-target",
    target_repository_name="tdi-action-preview",
)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ACTIONS_DIR = BACKEND_ROOT / "app" / "actions"


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    scripts = ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        asset = EnterpriseAssetModel(
            asset_key="repo-borealis-renderer",
            asset_type="REPOSITORY",
            name="Borealis Renderer Repository",
            criticality="MEDIUM",
            lifecycle_status="ACTIVE",
        )
        signal = SignalModel(
            signal_id=uuid4(),
            source_system="action-approval-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="action-approval-test",
                    source_reference="source-721",
                    captured_at=CREATED_AT,
                )
            ],
        )
        session.add(
            CandidateModel(
                candidate_id=CANDIDATE_ID,
                canonical_asset=asset,
                hypothesis="Potential missing request timeout",
                correlation_rationale=(
                    "Persisted Signals share an asset and problem family."
                ),
                signal_memberships=[CandidateSignalModel(signal=signal)],
            )
        )
        persist_human_decision(
            session,
            HumanDecision(
                human_decision_id=DECISION_ID,
                candidate_id=CANDIDATE_ID,
                sequence_number=1,
                decision_type=HumanDecisionType.VALIDATE,
                rationale="The Candidate is a validated structural issue.",
                requested_information=None,
                actor_reference=ACTOR.actor_reference,
                created_at=CREATED_AT,
            ),
        )
        persist_technical_debt(
            session,
            TechnicalDebt(
                technical_debt_id=TECHNICAL_DEBT_ID,
                source_candidate_id=CANDIDATE_ID,
                creation_human_decision_id=DECISION_ID,
                lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
                created_at=CREATED_AT,
            ),
        )
        session.commit()

    yield engine
    engine.dispose()


def _prepare(
    engine: Engine,
    *,
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
    new_id: Callable[[], UUID],
) -> object:
    with Session(engine) as session:
        return prepare_action_proposal(
            session,
            PrepareActionProposalCommand(technical_debt_id=technical_debt_id),
            ACTOR,
            PREPARATION,
            clock=lambda: CREATED_AT,
            new_id=new_id,
        )


def _approve(
    engine: Engine,
    proposal: object,
    *,
    fingerprint: str | None = None,
    actor: HumanActorContext = ACTOR,
    new_id: Callable[[], UUID] | None = None,
) -> ActionApproval:
    with Session(engine) as session:
        return approve_action_proposal(
            session,
            ApproveActionProposalCommand(
                technical_debt_id=proposal.technical_debt_id,  # type: ignore[attr-defined]
                action_proposal_id=proposal.action_proposal_id,  # type: ignore[attr-defined]
                expected_payload_fingerprint=(
                    fingerprint
                    if fingerprint is not None
                    else proposal.payload_fingerprint  # type: ignore[attr-defined]
                ),
            ),
            actor,
            clock=lambda: CREATED_AT,
            new_id=new_id,
        )


def _approval_count(engine: Engine) -> int:
    with Session(engine) as session:
        count = session.scalar(select(func.count()).select_from(ActionApprovalModel))
        return int(count or 0)


def test_exact_fingerprint_creates_approval(database_engine: Engine) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)

    approval = _approve(database_engine, proposal, new_id=lambda: APPROVAL_ID)

    assert approval.action_proposal_id == PROPOSAL_A_ID
    assert approval.payload_fingerprint == proposal.payload_fingerprint  # type: ignore[attr-defined]
    assert approval.actor_reference == ACTOR.actor_reference
    assert _approval_count(database_engine) == 1
    with Session(database_engine) as session:
        loaded = load_action_approval(session, APPROVAL_ID)
        assert loaded == approval


def test_stale_fingerprint_writes_nothing(database_engine: Engine) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    stale = ("0" if proposal.payload_fingerprint[0] != "0" else "1") + (  # type: ignore[index]
        proposal.payload_fingerprint[1:]  # type: ignore[index]
    )

    with pytest.raises(StaleActionProposalFingerprint, match="does not match"):
        _approve(database_engine, proposal, fingerprint=stale)

    assert _approval_count(database_engine) == 0


def test_same_proposal_second_approval_is_conflict(database_engine: Engine) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    _approve(database_engine, proposal, new_id=lambda: APPROVAL_ID)

    with pytest.raises(ActionProposalAlreadyApproved, match="already approved"):
        _approve(database_engine, proposal)

    assert _approval_count(database_engine) == 1


def test_competing_proposal_approval_is_conflict(database_engine: Engine) -> None:
    first = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    remaining = [PROPOSAL_B_ID]
    second = _prepare(database_engine, new_id=lambda: remaining.pop(0))
    _approve(database_engine, first)

    with pytest.raises(CompetingActionApprovalExists, match="competing"):
        _approve(database_engine, second)

    assert _approval_count(database_engine) == 1


def test_two_unapproved_proposals_may_coexist(database_engine: Engine) -> None:
    first = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    remaining = [PROPOSAL_B_ID]
    second = _prepare(database_engine, new_id=lambda: remaining.pop(0))

    assert first.action_proposal_id != second.action_proposal_id  # type: ignore[attr-defined]
    assert _approval_count(database_engine) == 0
    with Session(database_engine) as session:
        count = session.scalar(
            select(func.count())
            .select_from(ActionProposalModel)
            .where(ActionProposalModel.technical_debt_id == TECHNICAL_DEBT_ID)
        )
        assert count == 2


def test_approval_does_not_mutate_proposal_or_technical_debt(
    database_engine: Engine,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    with Session(database_engine) as session:
        before_proposal = load_action_proposal(session, PROPOSAL_A_ID)
        before_debt = session.get(TechnicalDebtModel, TECHNICAL_DEBT_ID)
        assert before_proposal is not None
        assert before_debt is not None
        before_status = before_debt.lifecycle_status
        before_created = before_debt.created_at

    _approve(database_engine, proposal)

    with Session(database_engine) as session:
        after_proposal = load_action_proposal(session, PROPOSAL_A_ID)
        after_debt = session.get(TechnicalDebtModel, TECHNICAL_DEBT_ID)
        assert after_proposal == before_proposal
        assert after_debt is not None
        assert after_debt.lifecycle_status == before_status
        assert after_debt.created_at == before_created


def test_missing_technical_debt_is_typed(database_engine: Engine) -> None:
    with pytest.raises(TechnicalDebtNotFound):
        with Session(database_engine) as session:
            approve_action_proposal(
                session,
                ApproveActionProposalCommand(
                    technical_debt_id=uuid4(),
                    action_proposal_id=uuid4(),
                    expected_payload_fingerprint="a" * 64,
                ),
                ACTOR,
            )

    assert _approval_count(database_engine) == 0


def test_missing_proposal_is_typed(database_engine: Engine) -> None:
    with pytest.raises(ActionProposalNotFound):
        with Session(database_engine) as session:
            approve_action_proposal(
                session,
                ApproveActionProposalCommand(
                    technical_debt_id=TECHNICAL_DEBT_ID,
                    action_proposal_id=uuid4(),
                    expected_payload_fingerprint="a" * 64,
                ),
                ACTOR,
            )

    assert _approval_count(database_engine) == 0


def test_unknown_technical_debt_is_typed_even_when_proposal_exists(
    database_engine: Engine,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)

    with pytest.raises(TechnicalDebtNotFound):
        with Session(database_engine) as session:
            approve_action_proposal(
                session,
                ApproveActionProposalCommand(
                    technical_debt_id=uuid4(),
                    action_proposal_id=proposal.action_proposal_id,  # type: ignore[attr-defined]
                    expected_payload_fingerprint=proposal.payload_fingerprint,  # type: ignore[attr-defined]
                ),
                ACTOR,
            )

    assert _approval_count(database_engine) == 0


def test_prepared_actor_is_server_owned(database_engine: Engine) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)
    actor = HumanActorContext(actor_reference="poc:governance-reviewer")

    approval = _approve(database_engine, proposal, actor=actor)

    assert approval.actor_reference == "poc:governance-reviewer"
    assert (
        "actor_reference" not in ApproveActionProposalCommand.__dataclass_fields__
    )


def test_approve_does_not_invoke_github_or_http(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("approve must not perform HTTP or GitHub calls")

    monkeypatch.setattr("httpx.Client", forbidden)
    monkeypatch.setattr("httpx.get", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)

    approval = _approve(database_engine, proposal)

    assert approval.action_proposal_id == PROPOSAL_A_ID
    assert _approval_count(database_engine) == 1


def test_actions_package_has_no_github_transport_or_agent_policy() -> None:
    imported: set[str] = set()
    source_chunks: list[str] = []
    for path in sorted(ACTIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        source_chunks.append(text)
        module = ast.parse(text, filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

    joined = "\n".join(source_chunks)
    assert not any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in imported
        for prefix in (
            "httpx",
            "app.infrastructure.github_issues",
            "app.connectors.github_issues",
            "app.agent.policy",
        )
    )
    assert "client.post(" not in joined
    assert "GITHUB_TOKEN" not in joined
    for path in sorted(ACTIONS_DIR.glob("*.py")):
        if path.name in {
            "verification.py",
            "github_issue_verifier.py",
            "contracts.py",
        }:
            continue
        assert "Verification" not in path.read_text(encoding="utf-8")


def test_approve_signature_requires_server_owned_actor() -> None:
    parameters = inspect.signature(approve_action_proposal).parameters

    assert list(parameters)[:3] == ["session", "command", "actor_context"]
    assert parameters["actor_context"].default is inspect.Parameter.empty


def test_active_session_transaction_is_rejected_before_writes(
    database_engine: Engine,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_A_ID)

    with Session(database_engine) as session:
        session.get(CandidateModel, CANDIDATE_ID)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            approve_action_proposal(
                session,
                ApproveActionProposalCommand(
                    technical_debt_id=TECHNICAL_DEBT_ID,
                    action_proposal_id=proposal.action_proposal_id,  # type: ignore[attr-defined]
                    expected_payload_fingerprint=proposal.payload_fingerprint,  # type: ignore[attr-defined]
                ),
                ACTOR,
            )

    assert _approval_count(database_engine) == 0
