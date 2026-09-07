from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
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
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.human_decision_persistence import (
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_persistence import (
    persist_technical_debt,
)
from app.signal_ingestion import NormalizedSignal

EXPECTED_HEAD = "20260907_01"


def _unique_column_sets(inspector: object, table_name: str) -> set[frozenset[str]]:
    unique_indexes = {
        frozenset(index["column_names"])
        for index in inspector.get_indexes(table_name)  # type: ignore[attr-defined]
        if index.get("unique")
    }
    try:
        unique_constraints = {
            frozenset(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)  # type: ignore[attr-defined]
        }
    except NotImplementedError:
        unique_constraints = set()
    return unique_constraints | unique_indexes


def _foreign_key_targets(inspector: object, table_name: str) -> set[str]:
    return {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys(table_name)  # type: ignore[attr-defined]
    }


def _nullable_columns(inspector: object, table_name: str) -> set[str]:
    return {
        column["name"]
        for column in inspector.get_columns(table_name)  # type: ignore[attr-defined]
        if column["nullable"]
    }


def _proposal(
    *,
    action_proposal_id: UUID,
    technical_debt_id: UUID,
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
        created_at=datetime(2026, 9, 7, 16, 0, tzinfo=UTC),
    )


@pytest.mark.integration
def test_mssql_migrates_action_proposal_schema() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        inspector = inspect(engine)
        assert "action_proposals" in set(inspector.get_table_names())
        assert _foreign_key_targets(inspector, "action_proposals") == {
            "technical_debts"
        }
        assert frozenset({"reconciliation_marker"}) in _unique_column_sets(
            inspector,
            "action_proposals",
        )
        assert frozenset({"technical_debt_id"}) not in _unique_column_sets(
            inspector,
            "action_proposals",
        )
        occupancy = frozenset({"technical_debt_id", "action_type"})
        assert occupancy not in _unique_column_sets(
            inspector,
            "action_proposals",
        )
        required = {
            "action_proposal_id",
            "technical_debt_id",
            "action_type",
            "target_repository_owner",
            "target_repository_name",
            "title",
            "body",
            "payload_fingerprint",
            "reconciliation_marker",
            "prepared_by",
            "created_at",
        }
        assert required.isdisjoint(_nullable_columns(inspector, "action_proposals"))
        technical_debt_columns = {
            column["name"] for column in inspector.get_columns("technical_debts")
        }
        assert technical_debt_columns == {
            "technical_debt_id",
            "source_candidate_id",
            "creation_human_decision_id",
            "lifecycle_status",
            "created_at",
        }

        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() == (
                EXPECTED_HEAD
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_mssql_persists_two_action_proposals_for_one_technical_debt() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    candidate_id = uuid4()
    signal_id = uuid4()
    evidence_id = uuid4()
    decision_id = uuid4()
    technical_debt_id = uuid4()
    first_proposal_id = uuid4()
    second_proposal_id = uuid4()
    timestamp = datetime(2026, 9, 7, 16, 0, tzinfo=UTC)

    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            persist_normalized_signal(
                session,
                NormalizedSignal(
                    signal=Signal(
                        signal_id=signal_id,
                        source_system="mssql-action-proposal-integration-test",
                        source_record_id=f"signal-{candidate_id}",
                        detected_at=timestamp,
                        signal_type="MISSING_TIMEOUT",
                        affected_asset=CanonicalAssetRef(
                            asset_key="repo-borealis-renderer",
                            asset_type=AssetType.REPOSITORY,
                        ),
                        severity="MEDIUM",
                        evidence_ids=frozenset({evidence_id}),
                    ),
                    evidence=frozenset(
                        {
                            Evidence(
                                evidence_id=evidence_id,
                                source_system="mssql-action-proposal-integration-test",
                                source_reference=f"evidence-{candidate_id}",
                                captured_at=timestamp,
                            )
                        }
                    ),
                ),
            )
            persist_candidate(
                session,
                Candidate(
                    candidate_id=candidate_id,
                    signal_ids=frozenset({signal_id}),
                    evidence_ids=frozenset({evidence_id}),
                    canonical_asset=CanonicalAssetRef(
                        asset_key="repo-borealis-renderer",
                        asset_type=AssetType.REPOSITORY,
                    ),
                    hypothesis="Potential missing request timeout",
                    correlation_rationale=(
                        "Signal shares the Candidate asset and problem family."
                    ),
                ),
            )
            persist_human_decision(
                session,
                HumanDecision(
                    human_decision_id=decision_id,
                    candidate_id=candidate_id,
                    sequence_number=1,
                    decision_type=HumanDecisionType.VALIDATE,
                    rationale="The Candidate is a validated structural issue.",
                    requested_information=None,
                    actor_reference="poc:local-reviewer",
                    created_at=timestamp,
                ),
            )
            persist_technical_debt(
                session,
                TechnicalDebt(
                    technical_debt_id=technical_debt_id,
                    source_candidate_id=candidate_id,
                    creation_human_decision_id=decision_id,
                    lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
                    created_at=timestamp,
                ),
            )
            persist_action_proposal(
                session,
                _proposal(
                    action_proposal_id=first_proposal_id,
                    technical_debt_id=technical_debt_id,
                ),
            )
            persist_action_proposal(
                session,
                _proposal(
                    action_proposal_id=second_proposal_id,
                    technical_debt_id=technical_debt_id,
                ),
            )
            session.commit()

        with Session(engine) as session:
            count = session.scalar(
                select(func.count())
                .select_from(ActionProposalModel)
                .where(ActionProposalModel.technical_debt_id == technical_debt_id)
            )
            assert count == 2
            session.add(
                ActionProposalModel(
                    action_proposal_id=uuid4(),
                    technical_debt_id=technical_debt_id,
                    action_type="CREATE_PULL_REQUEST",
                    target_repository_owner="tdi-demo-target",
                    target_repository_name="tdi-action-preview",
                    title="Technical debt: repo-borealis-renderer",
                    body="unsupported",
                    payload_fingerprint="0" * 64,
                    reconciliation_marker=f"tdiq-action-proposal:{uuid4()}",
                    prepared_by="poc:local-reviewer",
                    created_at=timestamp,
                )
            )
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()
    finally:
        with Session(engine) as session:
            session.execute(
                delete(ActionProposalModel).where(
                    ActionProposalModel.technical_debt_id == technical_debt_id
                )
            )
            session.execute(
                delete(TechnicalDebtModel).where(
                    TechnicalDebtModel.technical_debt_id == technical_debt_id
                )
            )
            session.execute(
                delete(HumanDecisionModel).where(
                    HumanDecisionModel.human_decision_id == decision_id
                )
            )
            session.execute(
                delete(CandidateSignalModel).where(
                    CandidateSignalModel.candidate_id == candidate_id
                )
            )
            session.execute(
                delete(CandidateModel).where(
                    CandidateModel.candidate_id == candidate_id
                )
            )
            session.execute(
                delete(EvidenceModel).where(EvidenceModel.evidence_id == evidence_id)
            )
            session.execute(
                delete(SignalModel).where(SignalModel.signal_id == signal_id)
            )
            session.commit()
        engine.dispose()
