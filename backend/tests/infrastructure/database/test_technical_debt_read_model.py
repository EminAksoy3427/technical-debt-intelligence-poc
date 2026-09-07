from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import apply_human_validation
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_read_model import (
    TechnicalDebtReadIntegrityError,
    list_technical_debt_summaries,
    load_technical_debt_detail,
)
from app.signal_ingestion import NormalizedSignal

CREATED_AT = datetime(2026, 9, 6, 20, 0, tzinfo=UTC)


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
        session.add(
            EnterpriseAssetModel(
                asset_key="svc-read-model",
                asset_type=AssetType.SERVICE.value,
                name="Read Model Service",
                criticality="MEDIUM",
                lifecycle_status="ACTIVE",
            )
        )
        session.commit()

    yield engine
    engine.dispose()


def _persist_candidate(session: Session, suffix: int) -> Candidate:
    evidence = Evidence(
        evidence_id=UUID(f"10000000-0000-0000-0000-{suffix:012d}"),
        source_system="technical-debt-read-model-test",
        source_reference=f"source-{suffix}",
        captured_at=CREATED_AT,
    )
    signal = Signal(
        signal_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        source_system="technical-debt-read-model-test",
        source_record_id=f"source-{suffix}",
        detected_at=CREATED_AT,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="svc-read-model",
            asset_type=AssetType.SERVICE,
        ),
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    persist_normalized_signal(
        session,
        NormalizedSignal(signal=signal, evidence=frozenset({evidence})),
    )
    candidate = Candidate(
        candidate_id=UUID(f"20000000-0000-0000-0000-{suffix:012d}"),
        signal_ids=frozenset({signal.signal_id}),
        evidence_ids=frozenset({evidence.evidence_id}),
        canonical_asset=signal.affected_asset,
        hypothesis=f"Hypothesis {suffix}",
        correlation_rationale="Exact asset and deterministic family.",
    )
    persist_candidate(session, candidate)
    return candidate


def test_list_is_empty_without_technical_debt(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        assert list_technical_debt_summaries(session) == ()


def test_list_and_detail_project_source_candidate_and_creation_decision(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        first = _persist_candidate(session, 1)
        second = _persist_candidate(session, 2)
        session.commit()

    with Session(database_engine) as session:
        earlier = apply_human_validation(
            session,
            HumanValidationCommand(
                candidate_id=first.candidate_id,
                decision=HumanDecisionType.VALIDATE,
                expected_governance_revision=0,
                rationale="First validated issue.",
            ),
            HumanActorContext(actor_reference="poc:local-reviewer"),
            clock=lambda: datetime(2026, 9, 6, 20, 1, tzinfo=UTC),
        )
    with Session(database_engine) as session:
        later = apply_human_validation(
            session,
            HumanValidationCommand(
                candidate_id=second.candidate_id,
                decision=HumanDecisionType.VALIDATE,
                expected_governance_revision=0,
                rationale="Second validated issue.",
            ),
            HumanActorContext(actor_reference="poc:local-reviewer"),
            clock=lambda: datetime(2026, 9, 6, 20, 2, tzinfo=UTC),
        )

    assert earlier.technical_debt is not None
    assert later.technical_debt is not None
    with Session(database_engine) as session:
        summaries = list_technical_debt_summaries(session)
        detail = load_technical_debt_detail(
            session,
            earlier.technical_debt.technical_debt_id,
        )

    assert [item.technical_debt.technical_debt_id for item in summaries] == [
        earlier.technical_debt.technical_debt_id,
        later.technical_debt.technical_debt_id,
    ]
    assert summaries[0].source_candidate.hypothesis == first.hypothesis
    assert detail is not None
    assert detail.source_candidate.candidate_id == first.candidate_id
    assert detail.creation_human_decision.human_decision_id == (
        earlier.human_decision.human_decision_id
    )
    assert detail.technical_debt.lifecycle_status.value == "REGISTERED"
    assert detail.action_proposals == ()
    assert detail.action_approvals == ()


def test_detail_returns_none_for_unknown_technical_debt(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        assert load_technical_debt_detail(session, uuid4()) is None


@pytest.mark.parametrize(
    "decision_type",
    (HumanDecisionType.REQUEST_INFO, HumanDecisionType.REJECT),
)
def test_detail_rejects_non_validate_creation_decision(
    database_engine: Engine,
    decision_type: HumanDecisionType,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(session, 11)
        session.commit()

    decision_id = uuid4()
    debt_id = uuid4()
    with Session(database_engine) as session:
        session.add(
            HumanDecisionModel(
                human_decision_id=decision_id,
                candidate_id=candidate.candidate_id,
                sequence_number=1,
                decision_type=decision_type.value,
                rationale=(
                    None
                    if decision_type is HumanDecisionType.REQUEST_INFO
                    else "Not a structural issue."
                ),
                requested_information=(
                    "Who owns this service?"
                    if decision_type is HumanDecisionType.REQUEST_INFO
                    else None
                ),
                actor_reference="poc:local-reviewer",
                created_at=CREATED_AT,
            )
        )
        session.add(
            TechnicalDebtModel(
                technical_debt_id=debt_id,
                source_candidate_id=candidate.candidate_id,
                creation_human_decision_id=decision_id,
                lifecycle_status="REGISTERED",
                created_at=CREATED_AT,
            )
        )
        session.commit()

    with Session(database_engine) as session:
        with pytest.raises(TechnicalDebtReadIntegrityError, match="VALIDATE"):
            load_technical_debt_detail(session, debt_id)


def _proposal_for_debt(
    technical_debt_id: UUID,
    action_proposal_id: UUID,
    created_at: datetime,
    title: str,
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
        created_at=created_at,
    )


def test_detail_projects_action_proposals_oldest_then_newest(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(session, 21)
        session.commit()

    with Session(database_engine) as session:
        created = apply_human_validation(
            session,
            HumanValidationCommand(
                candidate_id=candidate.candidate_id,
                decision=HumanDecisionType.VALIDATE,
                expected_governance_revision=0,
                rationale="Validated for ActionProposal projection.",
            ),
            HumanActorContext(actor_reference="poc:local-reviewer"),
            clock=lambda: datetime(2026, 9, 6, 20, 3, tzinfo=UTC),
        )

    assert created.technical_debt is not None
    technical_debt_id = created.technical_debt.technical_debt_id
    later_id = UUID("00000000-0000-0000-0000-000000000522")
    earlier_id = UUID("00000000-0000-0000-0000-000000000521")
    with Session(database_engine) as session:
        persist_action_proposal(
            session,
            _proposal_for_debt(
                technical_debt_id,
                later_id,
                CREATED_AT + timedelta(minutes=2),
                "Technical debt: later preview",
            ),
        )
        persist_action_proposal(
            session,
            _proposal_for_debt(
                technical_debt_id,
                earlier_id,
                CREATED_AT + timedelta(minutes=1),
                "Technical debt: earlier preview",
            ),
        )
        session.commit()

    with Session(database_engine) as session:
        detail = load_technical_debt_detail(session, technical_debt_id)

    assert detail is not None
    assert [item.action_proposal_id for item in detail.action_proposals] == [
        earlier_id,
        later_id,
    ]
    assert all(
        item.action_type is ActionType.CREATE_GITHUB_ISSUE
        for item in detail.action_proposals
    )
    assert not hasattr(detail.action_proposals[0], "approval")
    assert not hasattr(detail.action_proposals[0], "execution")
    assert not hasattr(detail.technical_debt, "action_proposal_id")
    assert detail.action_approvals == ()
