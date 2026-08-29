from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.synthetic_enterprise_estate import SYNTHETIC_INCIDENTS
from app.incident_ingestion import normalize_incident
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.incident_loading import (
    load_incidents_with_affected_assets,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    persist_normalized_signal,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
INCIDENT_KEYS = tuple(incident.incident_key for incident in SYNTHETIC_INCIDENTS)
ORBIT_INCIDENT_KEYS = ("inc-orbit-001", "inc-orbit-002", "inc-orbit-003")


def _remove_preexisting_incident_observations(session: Session) -> None:
    signal_ids = tuple(
        session.scalars(
            select(SignalModel.signal_id).where(
                SignalModel.source_system == "incident-management",
                SignalModel.source_record_id.in_(INCIDENT_KEYS),
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
def test_seeded_incidents_flow_to_mssql_and_deduplicate() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    command.upgrade(Config(str(BACKEND_ROOT / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        with Session(engine) as session:
            transaction = session.begin()
            try:
                seed_enterprise_estate(session)
                _remove_preexisting_incident_observations(session)

                loaded_incidents = load_incidents_with_affected_assets(
                    session,
                    incident_keys=INCIDENT_KEYS,
                )
                first_ingestion = tuple(
                    normalize_incident(
                        incident,
                        primary_affected_asset=affected_asset,
                    )
                    for incident, affected_asset in loaded_incidents
                )
                repeated_ingestion = tuple(
                    normalize_incident(
                        incident,
                        primary_affected_asset=affected_asset,
                    )
                    for incident, affected_asset in load_incidents_with_affected_assets(
                        session,
                        incident_keys=INCIDENT_KEYS,
                    )
                )

                first_results = [
                    persist_normalized_signal(session, normalized)
                    for normalized in first_ingestion
                ]
                repeated_results = [
                    persist_normalized_signal(session, normalized)
                    for normalized in repeated_ingestion
                ]
                scoped_signal_count = session.scalar(
                    select(func.count())
                    .select_from(SignalModel)
                    .where(
                        SignalModel.source_system == "incident-management",
                        SignalModel.source_record_id.in_(INCIDENT_KEYS),
                    )
                )
                scoped_evidence_count = session.scalar(
                    select(func.count())
                    .select_from(EvidenceModel)
                    .join(SignalModel)
                    .where(
                        SignalModel.source_system == "incident-management",
                        SignalModel.source_record_id.in_(INCIDENT_KEYS),
                    )
                )
                persisted_orbit_keys = set(
                    session.scalars(
                        select(SignalModel.source_record_id).where(
                            SignalModel.source_system == "incident-management",
                            SignalModel.source_record_id.in_(ORBIT_INCIDENT_KEYS),
                        )
                    )
                )
                persisted_orbit_signal_ids = set(
                    session.scalars(
                        select(SignalModel.signal_id).where(
                            SignalModel.source_system == "incident-management",
                            SignalModel.source_record_id.in_(ORBIT_INCIDENT_KEYS),
                        )
                    )
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()

    assert len(INCIDENT_KEYS) == 4
    assert len(loaded_incidents) == 4
    assert all(
        incident.started_at.utcoffset() is not None
        for incident, _ in loaded_incidents
    )
    assert first_results == [SignalPersistenceResult.CREATED] * 4
    assert repeated_results == [SignalPersistenceResult.DUPLICATE] * 4
    assert scoped_signal_count == 4
    assert scoped_evidence_count == 4
    assert persisted_orbit_keys == set(ORBIT_INCIDENT_KEYS)
    assert len(persisted_orbit_signal_ids) == 3
