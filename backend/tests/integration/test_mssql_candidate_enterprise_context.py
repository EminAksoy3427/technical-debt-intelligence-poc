from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationshipType,
    AssetType,
    OwnershipRole,
)
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_enterprise_context import (
    load_candidate_enterprise_context,
)
from app.infrastructure.database.candidate_persistence import (
    load_candidate,
    persist_candidate,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


@pytest.mark.integration
def test_mssql_loads_deterministic_candidate_enterprise_context() -> None:
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
                timestamp = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
                evidence = Evidence(
                    evidence_id=uuid4(),
                    source_system="mssql-candidate-context-test",
                    source_reference=f"context-{uuid4()}",
                    captured_at=timestamp,
                )
                signal = Signal(
                    signal_id=uuid4(),
                    source_system="mssql-candidate-context-test",
                    source_record_id=f"context-{uuid4()}",
                    detected_at=timestamp,
                    signal_type="MISSING_TIMEOUT",
                    affected_asset=CanonicalAssetRef(
                        asset_key="svc-orbit-catalog",
                        asset_type=AssetType.SERVICE,
                    ),
                    severity="MEDIUM",
                    evidence_ids=frozenset({evidence.evidence_id}),
                )
                persist_normalized_signal(
                    session,
                    NormalizedSignal(
                        signal=signal,
                        evidence=frozenset({evidence}),
                    ),
                )
                candidate = Candidate(
                    candidate_id=uuid4(),
                    signal_ids=frozenset({signal.signal_id}),
                    evidence_ids=frozenset({evidence.evidence_id}),
                    canonical_asset=signal.affected_asset,
                    hypothesis="Potential missing request timeout",
                    correlation_rationale=(
                        "One exact canonical asset and problem family."
                    ),
                )
                persist_candidate(session, candidate)

                assert load_candidate(session, candidate.candidate_id) == candidate
                first = load_candidate_enterprise_context(
                    session,
                    candidate.candidate_id,
                )
                repeated = load_candidate_enterprise_context(
                    session,
                    candidate.candidate_id,
                )

                assert first is not None
                assert repeated == first
                assert first.candidate_id == candidate.candidate_id
                assert first.enterprise_asset.asset_key == "svc-orbit-catalog"
                assert first.enterprise_asset.asset_type is AssetType.SERVICE
                assert first.enterprise_asset.criticality is AssetCriticality.HIGH
                assert (
                    first.enterprise_asset.lifecycle_status
                    is AssetLifecycleStatus.ACTIVE
                )
                assert [
                    (
                        item.asset_ownership.ownership_role,
                        item.team.team_key,
                    )
                    for item in first.enterprise_ownerships
                ] == [(OwnershipRole.PRIMARY, "team-orbit")]
                assert [
                    relationship.relationship_type
                    for relationship in first.direct_relationships
                ] == [
                    AssetRelationshipType.CONTAINS,
                    AssetRelationshipType.DEPENDS_ON,
                    AssetRelationshipType.DEPENDS_ON,
                    AssetRelationshipType.IMPLEMENTED_BY,
                ]
                assert {
                    incident.incident_key for incident in first.direct_incidents
                } == {
                    "inc-orbit-001",
                    "inc-orbit-002",
                    "inc-orbit-003",
                }
                assert all(
                    incident.primary_affected_asset_key == "svc-orbit-catalog"
                    for incident in first.direct_incidents
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
