from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    get_normalized_signal,
    persist_normalized_signal,
)
from app.signal_ingestion import NormalizedSignal


def _normalized_signal(source_record_id: str) -> NormalizedSignal:
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="mssql-integration-test",
        source_reference=source_record_id,
        captured_at=datetime(2026, 8, 28, 9, 0, tzinfo=UTC),
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="mssql-integration-test",
        source_record_id=source_record_id,
        detected_at=datetime(2026, 8, 28, 9, 0, tzinfo=UTC),
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="repo-borealis-renderer",
            asset_type=AssetType.REPOSITORY,
        ),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


@pytest.mark.integration
def test_mssql_persists_and_deduplicates_exact_source_observations() -> None:
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
                normalized_signal = _normalized_signal(f"mssql-test-{uuid4()}")

                assert (
                    persist_normalized_signal(session, normalized_signal)
                    is SignalPersistenceResult.CREATED
                )
                assert (
                    persist_normalized_signal(session, normalized_signal)
                    is SignalPersistenceResult.DUPLICATE
                )
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(SignalModel)
                        .where(
                            SignalModel.source_system
                            == normalized_signal.signal.source_system,
                            SignalModel.source_record_id
                            == normalized_signal.signal.source_record_id,
                        )
                    )
                    == 1
                )
                assert (
                    session.scalar(
                        select(func.count())
                        .select_from(EvidenceModel)
                        .where(
                            EvidenceModel.signal_id
                            == normalized_signal.signal.signal_id
                        )
                    )
                    == 1
                )
                assert (
                    get_normalized_signal(session, normalized_signal.provenance)
                    == normalized_signal
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
