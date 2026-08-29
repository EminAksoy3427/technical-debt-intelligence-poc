from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.git_history_ingestion import (
    GIT_SOURCE_SYSTEM,
    scan_and_normalize_git_repository,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    persist_normalized_signal,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ASSET_KEY = "repo-borealis-renderer"


def _remove_preexisting_git_observation(
    session: Session,
    source_record_id: str,
) -> None:
    signal_ids = tuple(
        session.scalars(
            select(SignalModel.signal_id).where(
                SignalModel.source_system == GIT_SOURCE_SYSTEM,
                SignalModel.source_record_id == source_record_id,
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
def test_git_satd_finding_flows_to_mssql_and_deduplicates(
    controlled_git_repository,
) -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    first_ingestion = scan_and_normalize_git_repository(
        controlled_git_repository.path,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )
    repeated_ingestion = scan_and_normalize_git_repository(
        controlled_git_repository.path,
        repository_asset_key=REPOSITORY_ASSET_KEY,
    )

    assert len(first_ingestion) == 1
    assert repeated_ingestion == first_ingestion

    normalized = first_ingestion[0]
    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                _remove_preexisting_git_observation(
                    session,
                    normalized.signal.source_record_id,
                )

                first_result = persist_normalized_signal(session, normalized)
                repeated_result = persist_normalized_signal(
                    session,
                    repeated_ingestion[0],
                )
                scoped_signal_count = session.scalar(
                    select(func.count())
                    .select_from(SignalModel)
                    .where(
                        SignalModel.source_system == GIT_SOURCE_SYSTEM,
                        SignalModel.source_record_id
                        == normalized.signal.source_record_id,
                    )
                )
                scoped_evidence_count = session.scalar(
                    select(func.count())
                    .select_from(EvidenceModel)
                    .join(SignalModel)
                    .where(
                        SignalModel.source_system == GIT_SOURCE_SYSTEM,
                        SignalModel.source_record_id
                        == normalized.signal.source_record_id,
                    )
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    assert first_result is SignalPersistenceResult.CREATED
    assert repeated_result is SignalPersistenceResult.DUPLICATE
    assert scoped_signal_count == 1
    assert scoped_evidence_count == 1
