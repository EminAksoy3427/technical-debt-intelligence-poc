from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    persist_normalized_signal,
)
from app.semgrep_ingestion import scan_and_normalize_semgrep_repository
from app.signal_ingestion import NormalizedSignal

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
CONTROLLED_REPOSITORY_ROOT = PROJECT_ROOT / "synthetic_repositories"
RULES_PATH = BACKEND_ROOT / "semgrep" / "rules.yml"
DETECTED_AT = datetime(2026, 8, 29, 12, 30, tzinfo=UTC)
REPOSITORY_ASSET_KEYS = (
    "repo-asteria-editor",
    "repo-borealis-renderer",
    "repo-orbit-catalog",
)


def _scan_controlled_repositories() -> tuple[NormalizedSignal, ...]:
    return tuple(
        normalized
        for asset_key in REPOSITORY_ASSET_KEYS
        for normalized in scan_and_normalize_semgrep_repository(
            CONTROLLED_REPOSITORY_ROOT / asset_key,
            repository_asset_key=asset_key,
            detected_at=DETECTED_AT,
            rules_path=RULES_PATH,
        )
    )


def _remove_preexisting_observations(
    session: Session,
    normalized_signals: tuple[NormalizedSignal, ...],
) -> None:
    source_record_ids = tuple(
        item.signal.source_record_id for item in normalized_signals
    )
    signal_ids = tuple(
        session.scalars(
            select(SignalModel.signal_id).where(
                SignalModel.source_system == "semgrep",
                SignalModel.source_record_id.in_(source_record_ids),
            )
        )
    )
    if signal_ids:
        session.execute(
            delete(EvidenceModel).where(EvidenceModel.signal_id.in_(signal_ids))
        )
        session.execute(
            delete(SignalModel).where(SignalModel.signal_id.in_(signal_ids))
        )
        session.flush()


@pytest.mark.integration
def test_controlled_semgrep_findings_flow_to_mssql_and_deduplicate() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    first_scan = _scan_controlled_repositories()
    repeated_scan = _scan_controlled_repositories()

    assert len(first_scan) == 3
    assert repeated_scan == first_scan

    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                _remove_preexisting_observations(session, first_scan)

                first_results = [
                    persist_normalized_signal(session, item) for item in first_scan
                ]
                repeated_results = [
                    persist_normalized_signal(session, item) for item in repeated_scan
                ]
                source_record_ids = tuple(
                    item.signal.source_record_id for item in first_scan
                )
                persisted_signal_count = session.scalar(
                    select(func.count())
                    .select_from(SignalModel)
                    .where(
                        SignalModel.source_system == "semgrep",
                        SignalModel.source_record_id.in_(source_record_ids),
                    )
                )
                persisted_evidence_count = session.scalar(
                    select(func.count())
                    .select_from(EvidenceModel)
                    .where(
                        EvidenceModel.signal_id.in_(
                            tuple(item.signal.signal_id for item in first_scan)
                        )
                    )
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    assert first_results == [SignalPersistenceResult.CREATED] * 3
    assert repeated_results == [SignalPersistenceResult.DUPLICATE] * 3
    assert persisted_signal_count == 3
    assert persisted_evidence_count == 3
