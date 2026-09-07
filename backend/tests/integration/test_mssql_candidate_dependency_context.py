from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import Settings
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_dependency_context import (
    load_candidate_dependency_context,
)
from app.infrastructure.database.candidate_persistence import (
    load_candidate,
    persist_candidate,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


def _persist_candidate(
    session: Session,
    *,
    asset_key: str,
    asset_type: AssetType,
) -> Candidate:
    timestamp = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="mssql-candidate-dependency-context-test",
        source_reference=f"dependency-context-{uuid4()}",
        captured_at=timestamp,
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="mssql-candidate-dependency-context-test",
        source_record_id=f"dependency-context-{uuid4()}",
        detected_at=timestamp,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    persist_normalized_signal(
        session,
        NormalizedSignal(signal=signal, evidence=frozenset({evidence})),
    )
    candidate = Candidate(
        candidate_id=uuid4(),
        signal_ids=frozenset({signal.signal_id}),
        evidence_ids=frozenset({evidence.evidence_id}),
        canonical_asset=signal.affected_asset,
        hypothesis="Potential missing request timeout",
        correlation_rationale="One exact canonical asset and problem family.",
    )
    persist_candidate(session, candidate)
    return candidate


def _keys(assets: tuple[CanonicalAssetRef, ...]) -> tuple[str, ...]:
    return tuple(asset.asset_key for asset in assets)


@pytest.mark.integration
def test_mssql_loads_deterministic_candidate_dependency_context() -> None:
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
                assert (
                    MigrationContext.configure(
                        session.connection()
                    ).get_current_revision()
                    == "20260907_04"
                )
                seed_enterprise_estate(session)
                service_candidate = _persist_candidate(
                    session,
                    asset_key="svc-orbit-catalog",
                    asset_type=AssetType.SERVICE,
                )
                repository_candidate = _persist_candidate(
                    session,
                    asset_key="repo-orbit-catalog",
                    asset_type=AssetType.REPOSITORY,
                )
                application_candidate = _persist_candidate(
                    session,
                    asset_key="app-asteria-canvas",
                    asset_type=AssetType.APPLICATION,
                )

                assert load_candidate(session, service_candidate.candidate_id) == (
                    service_candidate
                )
                service_context = load_candidate_dependency_context(
                    session,
                    service_candidate.candidate_id,
                )
                repeated_service_context = load_candidate_dependency_context(
                    session,
                    service_candidate.candidate_id,
                )
                repository_context = load_candidate_dependency_context(
                    session,
                    repository_candidate.candidate_id,
                )
                application_context = load_candidate_dependency_context(
                    session,
                    application_candidate.candidate_id,
                )

                assert service_context is not None
                assert repeated_service_context == service_context
                assert _keys(service_context.dependency_anchors) == (
                    "svc-orbit-catalog",
                )
                assert service_context.direct_dependencies == ()
                assert _keys(service_context.direct_dependents) == (
                    "svc-asteria-editor",
                    "svc-borealis-renderer",
                )
                assert service_context.reachable_dependents == (
                    service_context.direct_dependents
                )

                assert repository_context is not None
                assert _keys(repository_context.dependency_anchors) == (
                    "svc-orbit-catalog",
                )
                assert repository_context.direct_dependencies == (
                    service_context.direct_dependencies
                )
                assert repository_context.direct_dependents == (
                    service_context.direct_dependents
                )
                assert repository_context.reachable_dependents == (
                    service_context.reachable_dependents
                )

                assert application_context is not None
                assert _keys(application_context.dependency_anchors) == (
                    "svc-asteria-editor",
                    "svc-orbit-catalog",
                )
                assert _keys(application_context.direct_dependencies) == (
                    "svc-orbit-catalog",
                )
                assert _keys(application_context.direct_dependents) == (
                    "svc-asteria-editor",
                    "svc-borealis-renderer",
                )
                assert _keys(application_context.reachable_dependents) == (
                    "svc-borealis-renderer",
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
