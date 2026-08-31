from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.candidate_read_model import (
    list_candidate_summaries,
    load_candidate_detail,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.signal_ingestion import NormalizedSignal


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    backend_root = Path(__file__).resolve().parents[3]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        session.add(
            EnterpriseAssetModel(
                asset_key="svc-read-model",
                asset_type=AssetType.SERVICE.value,
                name="Read Model Service",
                criticality="MEDIUM",
                lifecycle_status="ACTIVE",
            )
        )
        session.commit()

    yield engine
    engine.dispose()


def _persist_candidate(session: Session) -> Candidate:
    signals: list[NormalizedSignal] = []
    for index, hour in ((2, 2), (1, 1)):
        evidence = Evidence(
            evidence_id=UUID(f"10000000-0000-0000-0000-{index:012d}"),
            source_system="candidate-read-model-test",
            source_reference=f"source-{index}",
            captured_at=datetime(2026, 8, 31, hour, 1, tzinfo=UTC),
        )
        signal = Signal(
            signal_id=UUID(f"00000000-0000-0000-0000-{index:012d}"),
            source_system="candidate-read-model-test",
            source_record_id=f"source-{index}",
            detected_at=datetime(2026, 8, 31, hour, 0, tzinfo=UTC),
            signal_type="MISSING_TIMEOUT",
            affected_asset=CanonicalAssetRef(
                asset_key="svc-read-model",
                asset_type=AssetType.SERVICE,
            ),
            evidence_ids=frozenset({evidence.evidence_id}),
        )
        normalized = NormalizedSignal(signal=signal, evidence=frozenset({evidence}))
        persist_normalized_signal(session, normalized)
        signals.append(normalized)

    candidate = Candidate(
        candidate_id=UUID("20000000-0000-0000-0000-000000000001"),
        signal_ids=frozenset(item.signal.signal_id for item in signals),
        evidence_ids=frozenset(
            evidence_id for item in signals for evidence_id in item.signal.evidence_ids
        ),
        canonical_asset=signals[0].signal.affected_asset,
        hypothesis="Potential missing request timeout",
        correlation_rationale="Exact asset and deterministic family.",
    )
    persist_candidate(session, candidate)
    return candidate


def test_read_model_assembles_exact_deterministic_facts_without_writes(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(session)
        session.commit()

        flushes = 0
        commits = 0

        def mark_flush(_session: Session, *_args: object) -> None:
            nonlocal flushes
            flushes += 1

        def mark_commit(_session: Session) -> None:
            nonlocal commits
            commits += 1

        event.listen(session, "before_flush", mark_flush)
        event.listen(session, "before_commit", mark_commit)

        summaries = list_candidate_summaries(session)
        detail = load_candidate_detail(session, candidate.candidate_id)
        repeated = load_candidate_detail(session, candidate.candidate_id)

    assert len(summaries) == 1
    assert summaries[0].candidate == candidate
    assert detail == repeated
    assert detail is not None
    assert detail.candidate == candidate
    assert [item.detected_at for item in detail.signals] == [
        datetime(2026, 8, 31, 1, 0, tzinfo=UTC),
        datetime(2026, 8, 31, 2, 0, tzinfo=UTC),
    ]
    assert [item.captured_at for item in detail.evidence] == [
        timestamp + timedelta(minutes=1)
        for timestamp in (
            datetime(2026, 8, 31, 1, 0, tzinfo=UTC),
            datetime(2026, 8, 31, 2, 0, tzinfo=UTC),
        )
    ]
    assert detail.enterprise_context.enterprise_asset.asset_key == "svc-read-model"
    assert detail.dependency_context.candidate_asset == candidate.canonical_asset
    assert flushes == 0
    assert commits == 0


def test_read_model_returns_none_for_unknown_candidate(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        assert (
            load_candidate_detail(
                session,
                UUID("30000000-0000-0000-0000-000000000001"),
            )
            is None
        )
