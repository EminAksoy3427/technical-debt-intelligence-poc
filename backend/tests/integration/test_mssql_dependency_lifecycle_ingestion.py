from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.connectors.dependency_lifecycle import (
    acquire_dependency_lifecycle_observations,
    normalize_dependency_lifecycle_observation,
)
from app.core.config import Settings
from app.dependency_lifecycle_ingestion import DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM
from app.infrastructure.database.dependency_lifecycle_loading import (
    resolve_dependency_lifecycle_affected_asset,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    persist_normalized_signal,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
SOURCE_PATH = (
    BACKEND_ROOT.parent
    / "synthetic_sources"
    / "dependency_lifecycle_findings.json"
)


def _remove_preexisting_lifecycle_observation(
    session: Session,
    source_record_id: str,
) -> None:
    signal_ids = tuple(
        session.scalars(
            select(SignalModel.signal_id).where(
                SignalModel.source_system == DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
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
def test_dependency_lifecycle_observation_flows_to_mssql_and_deduplicates() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    observation = acquire_dependency_lifecycle_observations(SOURCE_PATH)[0]
    finding = observation.record
    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                _remove_preexisting_lifecycle_observation(
                    session,
                    finding.source_record_id,
                )

                affected_asset = resolve_dependency_lifecycle_affected_asset(
                    session,
                    finding,
                )
                first_ingestion = normalize_dependency_lifecycle_observation(
                    observation,
                    affected_asset=affected_asset,
                )
                repeated_observation = acquire_dependency_lifecycle_observations(
                    SOURCE_PATH
                )[0]
                repeated_ingestion = normalize_dependency_lifecycle_observation(
                    repeated_observation,
                    affected_asset=resolve_dependency_lifecycle_affected_asset(
                        session,
                        repeated_observation.record,
                    ),
                )
                first_result = persist_normalized_signal(session, first_ingestion)
                repeated_result = persist_normalized_signal(session, repeated_ingestion)
                scoped_signal_count = session.scalar(
                    select(func.count())
                    .select_from(SignalModel)
                    .where(
                        SignalModel.source_system == DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
                        SignalModel.source_record_id == finding.source_record_id,
                    )
                )
                scoped_evidence_count = session.scalar(
                    select(func.count())
                    .select_from(EvidenceModel)
                    .join(SignalModel)
                    .where(
                        SignalModel.source_system == DEPENDENCY_LIFECYCLE_SOURCE_SYSTEM,
                        SignalModel.source_record_id == finding.source_record_id,
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
