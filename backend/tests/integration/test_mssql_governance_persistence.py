from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Thread
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import delete, event, func, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import (
    HumanActorContext,
    HumanValidationCommand,
    StaleGovernanceRevision,
)
from app.governance.human_validation import (
    AppliedHumanValidation,
    apply_human_validation,
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
    candidate_governance_boundary_statement,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.signal_ingestion import NormalizedSignal

EXPECTED_HEAD = "20260907_03"


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


@pytest.mark.integration
def test_mssql_migrates_human_decision_and_technical_debt_schema() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        inspector = inspect(engine)
        assert {"human_decisions", "technical_debts"} <= set(
            inspector.get_table_names()
        )
        assert _foreign_key_targets(inspector, "human_decisions") == {"candidates"}
        assert _foreign_key_targets(inspector, "technical_debts") == {
            "candidates",
            "human_decisions",
        }
        assert frozenset({"candidate_id", "sequence_number"}) in _unique_column_sets(
            inspector,
            "human_decisions",
        )
        assert frozenset({"source_candidate_id"}) in _unique_column_sets(
            inspector,
            "technical_debts",
        )
        assert frozenset({"creation_human_decision_id"}) in _unique_column_sets(
            inspector,
            "technical_debts",
        )

        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() == (
                EXPECTED_HEAD
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_mssql_serializes_same_revision_commands_and_creates_one_technical_debt() -> (
    None
):
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    captured_sql: list[str] = []

    def capture_sql(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        captured_sql.append(statement)

    event.listen(engine, "before_cursor_execute", capture_sql)
    candidate_id = uuid4()
    signal_id = uuid4()
    evidence_id = uuid4()
    barrier = Barrier(2)
    outcomes: list[AppliedHumanValidation | BaseException] = []

    def worker(actor_suffix: str) -> None:
        try:
            with Session(engine) as session:
                barrier.wait(timeout=10)
                result = apply_human_validation(
                    session,
                    HumanValidationCommand(
                        candidate_id=candidate_id,
                        decision=HumanDecisionType.VALIDATE,
                        expected_governance_revision=0,
                        rationale="The Candidate is a validated structural issue.",
                    ),
                    HumanActorContext(actor_reference=f"poc:{actor_suffix}"),
                    clock=lambda: datetime(2026, 9, 6, 18, 0, tzinfo=UTC),
                )
                outcomes.append(result)
        except BaseException as error:
            outcomes.append(error)

    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            timestamp = datetime(2026, 9, 6, 18, 0, tzinfo=UTC)
            persist_normalized_signal(
                session,
                NormalizedSignal(
                    signal=Signal(
                        signal_id=signal_id,
                        source_system="mssql-governance-integration-test",
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
                                source_system="mssql-governance-integration-test",
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
            session.commit()

        first = Thread(target=worker, args=("reviewer-a",))
        second = Thread(target=worker, args=("reviewer-b",))
        first.start()
        second.start()
        first.join(timeout=30)
        second.join(timeout=30)
        assert not first.is_alive()
        assert not second.is_alive()

        successes = [
            item for item in outcomes if isinstance(item, AppliedHumanValidation)
        ]
        conflicts = [
            item for item in outcomes if isinstance(item, StaleGovernanceRevision)
        ]
        assert len(outcomes) == 2
        assert len(successes) == 1
        assert len(conflicts) == 1
        assert successes[0].human_decision.sequence_number == 1
        assert successes[0].technical_debt is not None

        lock_sql = str(
            candidate_governance_boundary_statement(candidate_id).compile(
                dialect=engine.dialect
            )
        )
        assert "UPDLOCK" in lock_sql
        assert "HOLDLOCK" in lock_sql
        assert any(
            "UPDLOCK" in statement and "HOLDLOCK" in statement
            for statement in captured_sql
        )

        with Session(engine) as session:
            decision_count = session.scalar(
                select(func.count())
                .select_from(HumanDecisionModel)
                .where(HumanDecisionModel.candidate_id == candidate_id)
            )
            debt_count = session.scalar(
                select(func.count())
                .select_from(TechnicalDebtModel)
                .where(TechnicalDebtModel.source_candidate_id == candidate_id)
            )
            assert decision_count == 1
            assert debt_count == 1
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)
        with Session(engine) as session:
            session.execute(
                delete(TechnicalDebtModel).where(
                    TechnicalDebtModel.source_candidate_id == candidate_id
                )
            )
            session.execute(
                delete(HumanDecisionModel).where(
                    HumanDecisionModel.candidate_id == candidate_id
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
