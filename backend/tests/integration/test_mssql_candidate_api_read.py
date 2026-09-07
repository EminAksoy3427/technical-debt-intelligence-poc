from datetime import UTC, datetime, timedelta
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
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.candidate_read_model import (
    list_candidate_summaries,
    load_candidate_detail,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


def _persist_signal(
    session: Session,
    *,
    source_record_id: str,
    detected_at: datetime,
) -> NormalizedSignal:
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="mssql-candidate-api-read-test",
        source_reference=f"evidence:{source_record_id}",
        captured_at=detected_at + timedelta(minutes=1),
        reference_uri=f"https://synthetic.invalid/{source_record_id}",
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="mssql-candidate-api-read-test",
        source_record_id=source_record_id,
        detected_at=detected_at,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        ),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    normalized = NormalizedSignal(signal=signal, evidence=frozenset({evidence}))
    persist_normalized_signal(session, normalized)
    return normalized


@pytest.mark.integration
def test_mssql_candidate_api_read_boundary_is_exact_and_deterministic() -> None:
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
                source_prefix = str(uuid4())
                earlier = _persist_signal(
                    session,
                    source_record_id=f"{source_prefix}:earlier",
                    detected_at=datetime(2026, 8, 31, 9, 0, tzinfo=UTC),
                )
                later = _persist_signal(
                    session,
                    source_record_id=f"{source_prefix}:later",
                    detected_at=datetime(2026, 8, 31, 10, 0, tzinfo=UTC),
                )
                unrelated = _persist_signal(
                    session,
                    source_record_id=f"{source_prefix}:unrelated",
                    detected_at=datetime(2026, 8, 31, 8, 0, tzinfo=UTC),
                )
                candidate = Candidate(
                    candidate_id=uuid4(),
                    signal_ids=frozenset(
                        {earlier.signal.signal_id, later.signal.signal_id}
                    ),
                    evidence_ids=frozenset(
                        {
                            *earlier.signal.evidence_ids,
                            *later.signal.evidence_ids,
                        }
                    ),
                    canonical_asset=earlier.signal.affected_asset,
                    hypothesis="Potential missing request timeout",
                    correlation_rationale=(
                        "Exact canonical asset and deterministic problem family."
                    ),
                )
                persist_candidate(session, candidate)

                summaries = list_candidate_summaries(session)
                detail = load_candidate_detail(session, candidate.candidate_id)
                repeated = load_candidate_detail(session, candidate.candidate_id)

                assert any(
                    item.candidate.candidate_id == candidate.candidate_id
                    and len(item.candidate.signal_ids) == 2
                    and len(item.candidate.evidence_ids) == 2
                    for item in summaries
                )
                assert detail is not None
                assert repeated == detail
                assert detail.candidate == candidate
                assert [item.signal_id for item in detail.signals] == [
                    earlier.signal.signal_id,
                    later.signal.signal_id,
                ]
                assert unrelated.signal.signal_id not in {
                    item.signal_id for item in detail.signals
                }
                assert {item.evidence_id for item in detail.evidence} == (
                    set(candidate.evidence_ids)
                )
                assert detail.enterprise_context.enterprise_asset.asset_key == (
                    "svc-orbit-catalog"
                )
                assert detail.dependency_context.candidate_asset == (
                    candidate.canonical_asset
                )
                assert [
                    item.asset_key
                    for item in detail.dependency_context.reachable_dependents
                ] == ["svc-asteria-editor", "svc-borealis-renderer"]
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
