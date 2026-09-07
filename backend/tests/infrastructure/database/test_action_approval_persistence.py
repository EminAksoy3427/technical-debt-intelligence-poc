from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.dialects import mssql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.action_approvals import ActionApproval
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_approval_persistence import (
    list_action_approvals_for_technical_debt,
    load_action_approval,
    persist_action_approval,
    technical_debt_action_approval_boundary_statement,
)
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
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

CREATED_AT = datetime(2026, 9, 7, 19, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
SECOND_PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000502")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")
SECOND_APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000602")


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    backend_root = Path(__file__).resolve().parents[3]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
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
            source_system="action-approval-persistence-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="action-approval-persistence-test",
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
                actor_reference="poc:local-reviewer",
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
        persist_action_proposal(session, _proposal())
        persist_action_proposal(
            session,
            _proposal(action_proposal_id=SECOND_PROPOSAL_ID),
        )
        session.commit()

    yield engine
    engine.dispose()


def _proposal(
    *,
    action_proposal_id: UUID = PROPOSAL_ID,
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
) -> ActionProposal:
    marker = action_proposal_reconciliation_marker(action_proposal_id)
    payload = GitHubIssuePayload(
        title="Technical debt: repo-borealis-renderer",
        body=f"Technical debt remediation tracking issue\n\n{marker}\n",
    )
    return ActionProposal(
        action_proposal_id=action_proposal_id,
        technical_debt_id=technical_debt_id,
        action_type=ActionType.CREATE_GITHUB_ISSUE,
        target_repository_owner="tdi-demo-target",
        target_repository_name="tdi-action-preview",
        payload=payload,
        payload_fingerprint=canonical_action_payload_fingerprint(
            action_type=ActionType.CREATE_GITHUB_ISSUE.value,
            target_repository_owner="tdi-demo-target",
            target_repository_name="tdi-action-preview",
            title=payload.title,
            body=payload.body,
        ),
        reconciliation_marker=marker,
        prepared_by="poc:local-reviewer",
        created_at=CREATED_AT,
    )


def _approval(
    *,
    action_approval_id: UUID = APPROVAL_ID,
    action_proposal_id: UUID = PROPOSAL_ID,
    created_at: datetime = CREATED_AT,
) -> ActionApproval:
    proposal = _proposal(action_proposal_id=action_proposal_id)
    return ActionApproval(
        action_approval_id=action_approval_id,
        action_proposal_id=action_proposal_id,
        payload_fingerprint=proposal.payload_fingerprint,
        actor_reference="poc:local-reviewer",
        created_at=created_at,
    )


def test_action_approval_round_trips(database_engine: Engine) -> None:
    approval = _approval()
    with Session(database_engine) as session:
        persist_action_approval(session, approval)
        session.commit()

    with Session(database_engine) as session:
        loaded = load_action_approval(session, APPROVAL_ID)
        assert loaded == approval
        assert loaded is not None
        assert loaded.created_at.tzinfo is not None


def test_persistence_helper_flushes_but_does_not_commit(
    database_engine: Engine,
) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        event.listen(session, "before_commit", mark_commit)
        persist_action_approval(session, _approval())
        assert committed is False
        assert session.get(ActionApprovalModel, APPROVAL_ID) is not None

    with Session(database_engine) as session:
        assert session.get(ActionApprovalModel, APPROVAL_ID) is None


def test_duplicate_proposal_approval_is_rejected(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        session.flush()
        session.add(
            ActionApprovalModel(
                action_approval_id=SECOND_APPROVAL_ID,
                action_proposal_id=PROPOSAL_ID,
                payload_fingerprint=_proposal().payload_fingerprint,
                actor_reference="poc:other-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_list_approvals_is_oldest_then_newest(database_engine: Engine) -> None:
    later = _approval(
        action_approval_id=SECOND_APPROVAL_ID,
        action_proposal_id=SECOND_PROPOSAL_ID,
        created_at=CREATED_AT + timedelta(minutes=1),
    )
    earlier = _approval()
    with Session(database_engine) as session:
        persist_action_approval(session, later)
        persist_action_approval(session, earlier)
        session.commit()

    with Session(database_engine) as session:
        loaded = list_action_approvals_for_technical_debt(session, TECHNICAL_DEBT_ID)

    assert [item.action_approval_id for item in loaded] == [
        APPROVAL_ID,
        SECOND_APPROVAL_ID,
    ]


def test_approval_does_not_mutate_parent_tables(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        session.commit()

    with Session(database_engine) as session:
        debt = session.get(TechnicalDebtModel, TECHNICAL_DEBT_ID)
        proposal_count = session.scalar(
            select(func.count()).select_from(ActionProposalModel)
        )
        assert debt is not None
        assert debt.lifecycle_status == TechnicalDebtLifecycleStatus.REGISTERED.value
        assert proposal_count == 2


def test_mssql_lock_hint_is_dialect_specific() -> None:
    statement = technical_debt_action_approval_boundary_statement(TECHNICAL_DEBT_ID)
    mssql_sql = str(statement.compile(dialect=mssql.dialect()))
    sqlite_sql = str(statement.compile(dialect=sqlite.dialect()))

    assert "UPDLOCK" in mssql_sql
    assert "HOLDLOCK" in mssql_sql
    assert "UPDLOCK" not in sqlite_sql
    assert "HOLDLOCK" not in sqlite_sql
