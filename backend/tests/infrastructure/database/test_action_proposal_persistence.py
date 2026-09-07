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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import (
    list_action_proposals_for_technical_debt,
    load_action_proposal,
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

CREATED_AT = datetime(2026, 9, 7, 15, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
SECOND_PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000502")


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
            source_system="action-proposal-persistence-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="action-proposal-persistence-test",
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
        session.commit()

    yield engine
    engine.dispose()


def _proposal(
    *,
    action_proposal_id: UUID = PROPOSAL_ID,
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
    created_at: datetime = CREATED_AT,
    target_repository_owner: str = "tdi-demo-target",
    target_repository_name: str = "tdi-action-preview",
    title: str = "Technical debt: repo-borealis-renderer",
) -> ActionProposal:
    marker = action_proposal_reconciliation_marker(action_proposal_id)
    payload = GitHubIssuePayload(
        title=title,
        body=f"Technical debt remediation tracking issue\n\n{marker}\n",
    )
    return ActionProposal(
        action_proposal_id=action_proposal_id,
        technical_debt_id=technical_debt_id,
        action_type=ActionType.CREATE_GITHUB_ISSUE,
        target_repository_owner=target_repository_owner,
        target_repository_name=target_repository_name,
        payload=payload,
        payload_fingerprint=canonical_action_payload_fingerprint(
            action_type=ActionType.CREATE_GITHUB_ISSUE.value,
            target_repository_owner=target_repository_owner,
            target_repository_name=target_repository_name,
            title=payload.title,
            body=payload.body,
        ),
        reconciliation_marker=marker,
        prepared_by="poc:local-reviewer",
        created_at=created_at,
    )


def test_action_proposal_round_trips_timezone_aware_domain_contract(
    database_engine: Engine,
) -> None:
    proposal = _proposal()
    with Session(database_engine) as session:
        persist_action_proposal(session, proposal)
        session.commit()

    with Session(database_engine) as session:
        loaded = load_action_proposal(session, PROPOSAL_ID)
        assert loaded == proposal
        assert loaded is not None
        assert loaded.created_at.tzinfo is not None
        assert loaded.created_at.utcoffset() is not None
        assert loaded.payload_fingerprint == proposal.payload_fingerprint


def test_persistence_helper_flushes_but_does_not_commit(
    database_engine: Engine,
) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        event.listen(session, "before_commit", mark_commit)
        persist_action_proposal(session, _proposal())
        assert committed is False
        assert session.get(ActionProposalModel, PROPOSAL_ID) is not None

    with Session(database_engine) as session:
        assert session.get(ActionProposalModel, PROPOSAL_ID) is None


def test_two_proposals_for_the_same_technical_debt_are_persisted(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        persist_action_proposal(session, _proposal())
        persist_action_proposal(
            session,
            _proposal(action_proposal_id=SECOND_PROPOSAL_ID),
        )
        session.commit()

    with Session(database_engine) as session:
        count = session.scalar(
            select(func.count())
            .select_from(ActionProposalModel)
            .where(ActionProposalModel.technical_debt_id == TECHNICAL_DEBT_ID)
        )
        assert count == 2
        first = load_action_proposal(session, PROPOSAL_ID)
        second = load_action_proposal(session, SECOND_PROPOSAL_ID)
        assert first is not None
        assert second is not None
        assert first.reconciliation_marker != second.reconciliation_marker


def test_list_action_proposals_for_technical_debt_is_oldest_then_newest(
    database_engine: Engine,
) -> None:
    later = _proposal(
        action_proposal_id=SECOND_PROPOSAL_ID,
        created_at=CREATED_AT + timedelta(minutes=1),
        title="Technical debt: later preview",
    )
    earlier = _proposal(created_at=CREATED_AT)
    with Session(database_engine) as session:
        persist_action_proposal(session, later)
        persist_action_proposal(session, earlier)
        session.commit()

    with Session(database_engine) as session:
        loaded = list_action_proposals_for_technical_debt(session, TECHNICAL_DEBT_ID)

    assert [item.action_proposal_id for item in loaded] == [
        PROPOSAL_ID,
        SECOND_PROPOSAL_ID,
    ]
    assert loaded[0].created_at < loaded[1].created_at


def test_duplicate_reconciliation_marker_is_rejected(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persist_action_proposal(session, _proposal())
        session.flush()
        session.add(
            ActionProposalModel(
                action_proposal_id=SECOND_PROPOSAL_ID,
                technical_debt_id=TECHNICAL_DEBT_ID,
                action_type=ActionType.CREATE_GITHUB_ISSUE.value,
                target_repository_owner="tdi-demo-target",
                target_repository_name="tdi-action-preview",
                title="Technical debt: repo-borealis-renderer",
                body="duplicate marker body",
                payload_fingerprint="0" * 64,
                reconciliation_marker=action_proposal_reconciliation_marker(PROPOSAL_ID),
                prepared_by="poc:other-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_database_rejects_unsupported_action_type(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        session.add(
            ActionProposalModel(
                action_proposal_id=PROPOSAL_ID,
                technical_debt_id=TECHNICAL_DEBT_ID,
                action_type="CREATE_PULL_REQUEST",
                target_repository_owner="tdi-demo-target",
                target_repository_name="tdi-action-preview",
                title="Technical debt: repo-borealis-renderer",
                body="unsupported type",
                payload_fingerprint="0" * 64,
                reconciliation_marker=action_proposal_reconciliation_marker(PROPOSAL_ID),
                prepared_by="poc:local-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_technical_debt_parent_table_is_unaltered(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persisted = session.get(TechnicalDebtModel, TECHNICAL_DEBT_ID)
        assert persisted is not None
        assert (
            persisted.lifecycle_status
            == TechnicalDebtLifecycleStatus.REGISTERED.value
        )
        assert not hasattr(persisted, "action_proposal_id")
        persist_action_proposal(session, _proposal())
        session.commit()

    with Session(database_engine) as session:
        persisted = session.get(TechnicalDebtModel, TECHNICAL_DEBT_ID)
        assert persisted is not None
        assert (
            persisted.lifecycle_status
            == TechnicalDebtLifecycleStatus.REGISTERED.value
        )
        proposal_count = session.scalar(
            select(func.count()).select_from(ActionProposalModel)
        )
        assert proposal_count == 1
