import importlib
import inspect
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

from app.dependency_lifecycle_ingestion import normalize_dependency_lifecycle_finding
from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.domain.synthetic_enterprise_estate import SYNTHETIC_INCIDENTS
from app.git_history_ingestion import scan_and_normalize_git_repository
from app.incident_ingestion import normalize_incident
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import (
    SignalPersistenceResult,
    get_normalized_signal,
    persist_normalized_signal,
)
from app.infrastructure.dependency_lifecycle import load_dependency_lifecycle_findings
from app.infrastructure.semgrep import SemgrepFinding
from app.semgrep_ingestion import normalize_semgrep_finding
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
        session.add(
            EnterpriseAssetModel(
                asset_key="repo-borealis-renderer",
                asset_type=AssetType.REPOSITORY.value,
                name="Borealis Renderer Repository",
                criticality="MEDIUM",
                lifecycle_status="ACTIVE",
            )
        )
        session.add(
            EnterpriseAssetModel(
                asset_key="svc-orbit-catalog",
                asset_type=AssetType.SERVICE.value,
                name="Orbit Catalog Service",
                criticality="HIGH",
                lifecycle_status="ACTIVE",
            )
        )
        session.commit()

    yield engine
    engine.dispose()


def _normalized_signal(
    *,
    signal_id: UUID | None = None,
    evidence_id: UUID | None = None,
    source_system: str = "semgrep",
    source_record_id: str = "repo-borealis-renderer:renderer_client.py:6",
    detected_at: datetime = datetime(2026, 8, 28, 9, 0, tzinfo=UTC),
    signal_type: str = "MISSING_TIMEOUT",
    asset_key: str = "repo-borealis-renderer",
    asset_type: AssetType = AssetType.REPOSITORY,
    severity: str | None = "MEDIUM",
    source_reference: str = "renderer_client.py:6",
    reference_uri: str | None = "https://findings.example/renderer-client-6",
) -> NormalizedSignal:
    evidence = Evidence(
        evidence_id=evidence_id or uuid4(),
        source_system=source_system,
        source_reference=source_reference,
        captured_at=detected_at,
        reference_uri=reference_uri,
    )
    signal = Signal(
        signal_id=signal_id or uuid4(),
        source_system=source_system,
        source_record_id=source_record_id,
        detected_at=detected_at,
        signal_type=signal_type,
        affected_asset=CanonicalAssetRef(
            asset_key=asset_key,
            asset_type=asset_type,
        ),
        severity=severity,
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def _record_count(
    session: Session,
    model_type: type[SignalModel] | type[EvidenceModel],
) -> int:
    return session.scalar(select(func.count()).select_from(model_type)) or 0


def test_persisted_normalized_signal_round_trips_canonical_contract(
    database_engine: Engine,
) -> None:
    normalized_signal = _normalized_signal(
        signal_id=UUID("00000000-0000-0000-0000-000000000301"),
        evidence_id=UUID("00000000-0000-0000-0000-000000000401"),
    )

    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, normalized_signal)
            is SignalPersistenceResult.CREATED
        )
        session.commit()

    with Session(database_engine) as session:
        reconstructed = get_normalized_signal(
            session,
            SourceObservationRef(
                source_system=normalized_signal.signal.source_system,
                source_record_id=normalized_signal.signal.source_record_id,
            ),
        )

    assert reconstructed == normalized_signal
    assert reconstructed is not None
    assert reconstructed.provenance == SourceObservationRef(
        source_system="semgrep",
        source_record_id="repo-borealis-renderer:renderer_client.py:6",
    )
    assert reconstructed.signal.affected_asset == CanonicalAssetRef(
        asset_key="repo-borealis-renderer",
        asset_type=AssetType.REPOSITORY,
    )


def test_repeated_source_observation_returns_duplicate_without_duplicate_evidence(
    database_engine: Engine,
) -> None:
    first = _normalized_signal()
    repeated = _normalized_signal(
        source_record_id=first.signal.source_record_id,
        signal_type="DIFFERENT_CANONICAL_MEANING",
    )

    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, first) is SignalPersistenceResult.CREATED
        )
        assert (
            persist_normalized_signal(session, repeated)
            is SignalPersistenceResult.DUPLICATE
        )
        assert _record_count(session, SignalModel) == 1
        assert _record_count(session, EvidenceModel) == 1
        reconstructed = get_normalized_signal(session, first.provenance)

    assert reconstructed == first


def test_different_source_record_ids_create_distinct_signals(
    database_engine: Engine,
) -> None:
    first = _normalized_signal(source_record_id="finding-001")
    second = _normalized_signal(source_record_id="finding-002")

    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, first) is SignalPersistenceResult.CREATED
        )
        assert (
            persist_normalized_signal(session, second)
            is SignalPersistenceResult.CREATED
        )
        assert _record_count(session, SignalModel) == 2
        assert _record_count(session, EvidenceModel) == 2


def test_distinct_orbit_incident_observations_are_not_correlated(
    database_engine: Engine,
) -> None:
    incident_record_ids = ("inc-orbit-001", "inc-orbit-002", "inc-orbit-003")

    with Session(database_engine) as session:
        for record_id in incident_record_ids:
            normalized_signal = _normalized_signal(
                source_system="incident-management",
                source_record_id=record_id,
                signal_type="OPERATIONAL_INCIDENT",
                asset_key="svc-orbit-catalog",
                asset_type=AssetType.SERVICE,
                source_reference=record_id,
            )
            assert (
                persist_normalized_signal(session, normalized_signal)
                is SignalPersistenceResult.CREATED
            )

        persisted_record_ids = set(
            session.scalars(
                select(SignalModel.source_record_id).where(
                    SignalModel.source_system == "incident-management"
                )
            )
        )

    assert persisted_record_ids == set(incident_record_ids)


def test_database_unique_constraint_prevents_duplicate_source_observations(
    database_engine: Engine,
) -> None:
    normalized_signal = _normalized_signal(source_record_id="finding-unique")

    with Session(database_engine) as session:
        persist_normalized_signal(session, normalized_signal)
        session.commit()

    with Session(database_engine) as session:
        affected_asset = session.scalar(
            select(EnterpriseAssetModel).where(
                EnterpriseAssetModel.asset_key == "repo-borealis-renderer"
            )
        )
        assert affected_asset is not None
        session.add(
            SignalModel(
                signal_id=uuid4(),
                source_system=normalized_signal.signal.source_system,
                source_record_id=normalized_signal.signal.source_record_id,
                detected_at=normalized_signal.signal.detected_at,
                signal_type=normalized_signal.signal.signal_type,
                affected_asset=affected_asset,
                severity=normalized_signal.signal.severity,
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

    with Session(database_engine) as session:
        assert _record_count(session, SignalModel) == 1


def test_signal_affected_asset_must_resolve_to_catalog_asset(
    database_engine: Engine,
) -> None:
    unknown_asset_signal = _normalized_signal(asset_key="repo-not-in-catalog")

    with Session(database_engine) as session:
        with pytest.raises(ValueError, match="does not exist"):
            persist_normalized_signal(session, unknown_asset_signal)


def test_database_foreign_key_protects_signal_affected_asset(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        session.add(
            SignalModel(
                signal_id=uuid4(),
                source_system="semgrep",
                source_record_id="foreign-key-check",
                detected_at=datetime(2026, 8, 28, 9, 0, tzinfo=UTC),
                signal_type="MISSING_TIMEOUT",
                affected_asset_id=99999,
                severity="MEDIUM",
            )
        )

        with pytest.raises(IntegrityError):
            session.flush()


def test_ingestion_persistence_does_not_reference_candidates_or_ground_truth() -> None:
    persistence_source = inspect.getsource(
        importlib.import_module("app.infrastructure.database.signal_persistence")
    ).lower()

    assert "candidate" not in persistence_source
    assert "ground_truth" not in persistence_source


def test_normalized_semgrep_finding_is_created_then_deduplicated(
    database_engine: Engine,
) -> None:
    finding = SemgrepFinding(
        rule_id="tdi.python.missing-timeout",
        relative_path="renderer_client.py",
        start_line=5,
        start_column=10,
        end_line=5,
        end_column=52,
        message="A urllib request is made without an explicit timeout.",
        severity="WARNING",
    )
    normalized_signal = normalize_semgrep_finding(
        finding,
        repository_asset_key="repo-borealis-renderer",
        detected_at=datetime(2026, 8, 29, 12, 30, tzinfo=UTC),
    )

    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, normalized_signal)
            is SignalPersistenceResult.CREATED
        )
        assert (
            persist_normalized_signal(session, normalized_signal)
            is SignalPersistenceResult.DUPLICATE
        )
        assert _record_count(session, SignalModel) == 1
        assert _record_count(session, EvidenceModel) == 1


def test_normalized_orbit_incidents_are_created_then_deduplicated(
    database_engine: Engine,
) -> None:
    orbit_incidents = tuple(
        incident
        for incident in SYNTHETIC_INCIDENTS
        if incident.primary_affected_asset_key == "svc-orbit-catalog"
    )
    normalized_incidents = tuple(
        normalize_incident(
            incident,
            primary_affected_asset=CanonicalAssetRef(
                asset_key=incident.primary_affected_asset_key,
                asset_type=AssetType.SERVICE,
            ),
        )
        for incident in orbit_incidents
    )

    with Session(database_engine) as session:
        first_results = [
            persist_normalized_signal(session, normalized)
            for normalized in normalized_incidents
        ]
        repeated_results = [
            persist_normalized_signal(session, normalized)
            for normalized in normalized_incidents
        ]

        assert first_results == [SignalPersistenceResult.CREATED] * 3
        assert repeated_results == [SignalPersistenceResult.DUPLICATE] * 3
        assert _record_count(session, SignalModel) == 3
        assert _record_count(session, EvidenceModel) == 3


def test_normalized_dependency_lifecycle_finding_is_created_then_deduplicated(
    database_engine: Engine,
) -> None:
    source_path = (
        Path(__file__).resolve().parents[4]
        / "synthetic_sources"
        / "dependency_lifecycle_findings.json"
    )
    finding = load_dependency_lifecycle_findings(source_path)[0]
    normalized_signal = normalize_dependency_lifecycle_finding(
        finding,
        affected_asset=CanonicalAssetRef(
            asset_key=finding.affected_asset_key,
            asset_type=AssetType.REPOSITORY,
        ),
    )

    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, normalized_signal)
            is SignalPersistenceResult.CREATED
        )
        assert (
            persist_normalized_signal(session, normalized_signal)
            is SignalPersistenceResult.DUPLICATE
        )
        assert _record_count(session, SignalModel) == 1
        assert _record_count(session, EvidenceModel) == 1


def test_normalized_git_finding_is_created_then_deduplicated(
    database_engine: Engine,
    controlled_git_repository,
) -> None:
    normalized_signals = scan_and_normalize_git_repository(
        controlled_git_repository.path,
        repository_asset_key="repo-borealis-renderer",
    )

    assert len(normalized_signals) == 1
    with Session(database_engine) as session:
        assert (
            persist_normalized_signal(session, normalized_signals[0])
            is SignalPersistenceResult.CREATED
        )
        assert (
            persist_normalized_signal(session, normalized_signals[0])
            is SignalPersistenceResult.DUPLICATE
        )
        assert _record_count(session, SignalModel) == 1
        assert _record_count(session, EvidenceModel) == 1
