from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.candidate_persistence import (
    CandidatePersistenceResult,
    load_candidate,
    persist_candidate,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


def _normalized_signal(source_record_id: str) -> NormalizedSignal:
    timestamp = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="mssql-candidate-integration-test",
        source_reference=source_record_id,
        captured_at=timestamp,
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="mssql-candidate-integration-test",
        source_record_id=source_record_id,
        detected_at=timestamp,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="repo-borealis-renderer",
            asset_type=AssetType.REPOSITORY,
        ),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def _candidate(
    *signals: NormalizedSignal,
    candidate_id: UUID | None = None,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id or uuid4(),
        signal_ids=frozenset(item.signal.signal_id for item in signals),
        evidence_ids=frozenset(
            evidence_id for item in signals for evidence_id in item.signal.evidence_ids
        ),
        canonical_asset=CanonicalAssetRef(
            asset_key="repo-borealis-renderer",
            asset_type=AssetType.REPOSITORY,
        ),
        hypothesis="Potential missing request timeout",
        correlation_rationale="Signals share one canonical asset and problem family.",
    )


@pytest.mark.integration
def test_mssql_upgrades_and_persists_candidate_snapshots() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                first_signal = _normalized_signal(f"mssql-candidate-{uuid4()}")
                second_signal = _normalized_signal(f"mssql-candidate-{uuid4()}")
                persist_normalized_signal(session, first_signal)
                persist_normalized_signal(session, second_signal)

                candidate = _candidate(first_signal)
                assert (
                    persist_candidate(session, candidate)
                    is CandidatePersistenceResult.CREATED
                )
                assert load_candidate(session, candidate.candidate_id) == candidate
                assert (
                    persist_candidate(session, candidate)
                    is CandidatePersistenceResult.UNCHANGED
                )

                expanded = _candidate(
                    first_signal,
                    second_signal,
                    candidate_id=candidate.candidate_id,
                )
                assert (
                    persist_candidate(session, expanded)
                    is CandidatePersistenceResult.UPDATED
                )
                assert load_candidate(session, candidate.candidate_id) == expanded
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(CandidateSignalModel)
                        .where(
                            CandidateSignalModel.candidate_id == candidate.candidate_id
                        )
                    )
                    == 2
                )
                assert (
                    session.scalar(select(func.count()).select_from(CandidateModel))
                    >= 1
                )

                unknown_signal_candidate = Candidate(
                    candidate_id=uuid4(),
                    signal_ids=frozenset({uuid4()}),
                    evidence_ids=frozenset({uuid4()}),
                    canonical_asset=candidate.canonical_asset,
                    hypothesis="Potential missing request timeout",
                    correlation_rationale="Signals must be present before persistence.",
                )
                with pytest.raises(ValueError, match="not persisted"):
                    persist_candidate(session, unknown_signal_candidate)
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
