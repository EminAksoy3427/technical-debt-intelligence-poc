from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

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
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import SignalModel
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
    config = Config(str(backend_root / "alembic.ini"))
    scripts = ScriptDirectory.from_config(config)
    revisions = list(scripts.walk_revisions(base="base", head="heads"))

    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        session.add_all(
            [
                EnterpriseAssetModel(
                    asset_key="repo-borealis-renderer",
                    asset_type=AssetType.REPOSITORY.value,
                    name="Borealis Renderer Repository",
                    criticality="MEDIUM",
                    lifecycle_status="ACTIVE",
                ),
                EnterpriseAssetModel(
                    asset_key="svc-orbit-catalog",
                    asset_type=AssetType.SERVICE.value,
                    name="Orbit Catalog Service",
                    criticality="HIGH",
                    lifecycle_status="ACTIVE",
                ),
            ]
        )
        session.commit()

    yield engine
    engine.dispose()


def _normalized_signal(
    *,
    signal_id: UUID | None = None,
    evidence_id: UUID | None = None,
    source_record_id: str | None = None,
    asset_key: str = "repo-borealis-renderer",
    asset_type: AssetType = AssetType.REPOSITORY,
) -> NormalizedSignal:
    timestamp = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
    resolved_signal_id = signal_id or uuid4()
    evidence = Evidence(
        evidence_id=evidence_id or uuid4(),
        source_system="candidate-persistence-test",
        source_reference=source_record_id or f"source-{resolved_signal_id}",
        captured_at=timestamp,
    )
    signal = Signal(
        signal_id=resolved_signal_id,
        source_system="candidate-persistence-test",
        source_record_id=source_record_id or f"source-{resolved_signal_id}",
        detected_at=timestamp,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def _persist_signal(session: Session, **kwargs: object) -> NormalizedSignal:
    normalized_signal = _normalized_signal(**kwargs)  # type: ignore[arg-type]
    persist_normalized_signal(session, normalized_signal)
    return normalized_signal


def _candidate(
    *signals: NormalizedSignal,
    candidate_id: UUID | None = None,
    asset_key: str = "repo-borealis-renderer",
    asset_type: AssetType = AssetType.REPOSITORY,
    hypothesis: str = "Potential missing request timeout",
    correlation_rationale: str = (
        "Signals share one canonical asset and problem family."
    ),
    evidence_ids: frozenset[UUID] | None = None,
) -> Candidate:
    return Candidate(
        candidate_id=candidate_id or uuid4(),
        signal_ids=frozenset(item.signal.signal_id for item in signals),
        evidence_ids=evidence_ids
        or frozenset(
            evidence_id for item in signals for evidence_id in item.signal.evidence_ids
        ),
        canonical_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        hypothesis=hypothesis,
        correlation_rationale=correlation_rationale,
    )


def test_candidate_persists_and_loads_the_canonical_contract(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        signal = _persist_signal(
            session,
            signal_id=UUID("00000000-0000-0000-0000-000000000501"),
            evidence_id=UUID("00000000-0000-0000-0000-000000000601"),
        )
        candidate = _candidate(
            signal,
            candidate_id=UUID("00000000-0000-0000-0000-000000000701"),
        )

        assert (
            persist_candidate(session, candidate) is CandidatePersistenceResult.CREATED
        )
        session.commit()

    with Session(database_engine) as session:
        assert load_candidate(session, candidate.candidate_id) == candidate


def test_exact_candidate_snapshot_is_unchanged_and_does_not_commit(
    database_engine: Engine,
) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        signal = _persist_signal(session)
        candidate = _candidate(signal)
        assert (
            persist_candidate(session, candidate) is CandidatePersistenceResult.CREATED
        )
        session.commit()

        event.listen(session, "before_commit", mark_commit)
        assert (
            persist_candidate(session, candidate)
            is CandidatePersistenceResult.UNCHANGED
        )
        assert committed is False


def test_candidate_snapshot_updates_and_synchronizes_membership(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        first_signal = _persist_signal(session, source_record_id="signal-first")
        second_signal = _persist_signal(session, source_record_id="signal-second")
        candidate = _candidate(first_signal)
        assert (
            persist_candidate(session, candidate) is CandidatePersistenceResult.CREATED
        )

        expanded = _candidate(
            first_signal,
            second_signal,
            candidate_id=candidate.candidate_id,
        )
        assert (
            persist_candidate(session, expanded) is CandidatePersistenceResult.UPDATED
        )
        assert load_candidate(session, candidate.candidate_id) == expanded

        reduced = _candidate(second_signal, candidate_id=candidate.candidate_id)
        assert persist_candidate(session, reduced) is CandidatePersistenceResult.UPDATED
        assert load_candidate(session, candidate.candidate_id) == reduced
        assert session.get(SignalModel, first_signal.signal.signal_id) is not None


def test_candidate_membership_is_normalized_and_foreign_key_constrained(
    database_engine: Engine,
) -> None:
    table = CandidateSignalModel.__table__
    assert set(table.columns.keys()) == {"candidate_id", "signal_id"}
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "candidates.candidate_id",
        "signals.signal_id",
    }

    with Session(database_engine) as session:
        session.add(CandidateSignalModel(candidate_id=uuid4(), signal_id=uuid4()))
        with pytest.raises(IntegrityError):
            session.flush()


def test_unknown_signal_and_evidence_mismatch_are_rejected(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        known_signal = _persist_signal(session)
        unknown_candidate = Candidate(
            candidate_id=uuid4(),
            signal_ids=frozenset({uuid4()}),
            evidence_ids=frozenset({uuid4()}),
            canonical_asset=known_signal.signal.affected_asset,
            hypothesis="Potential missing request timeout",
            correlation_rationale="A Signal is expected to be persisted first.",
        )
        with pytest.raises(ValueError, match="not persisted"):
            persist_candidate(session, unknown_candidate)

        mismatched_evidence = _candidate(
            known_signal,
            evidence_ids=frozenset({uuid4()}),
        )
        with pytest.raises(ValueError, match="do not match"):
            persist_candidate(session, mismatched_evidence)


def test_conflicting_candidate_asset_is_rejected(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        repository_signal = _persist_signal(session, source_record_id="repository")
        service_signal = _persist_signal(
            session,
            source_record_id="service",
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        )
        candidate = _candidate(repository_signal)
        assert (
            persist_candidate(session, candidate) is CandidatePersistenceResult.CREATED
        )

        conflicting = _candidate(
            service_signal,
            candidate_id=candidate.candidate_id,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        )
        with pytest.raises(ValueError, match="conflicts"):
            persist_candidate(session, conflicting)


def test_candidate_persistence_is_deterministic_and_creates_no_lifecycle_state(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        signal = _persist_signal(session)
        candidate = _candidate(signal)

        assert (
            persist_candidate(session, candidate) is CandidatePersistenceResult.CREATED
        )
        assert (
            persist_candidate(session, candidate)
            is CandidatePersistenceResult.UNCHANGED
        )
        assert session.scalar(select(func.count()).select_from(CandidateModel)) == 1
        assert (
            session.scalar(select(func.count()).select_from(CandidateSignalModel)) == 1
        )
        assert {"status", "risk", "effort", "owner", "validation"}.isdisjoint(
            CandidateModel.__table__.columns.keys()
        )
