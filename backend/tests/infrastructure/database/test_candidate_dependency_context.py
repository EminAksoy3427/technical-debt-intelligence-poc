import importlib
import inspect
from collections.abc import Iterator
from dataclasses import FrozenInstanceError, fields
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, update
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationshipType,
    AssetType,
)
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_dependency_context import (
    CandidateDependencyContextIntegrityError,
    load_candidate_dependency_context,
)
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_models import (
    AssetRelationshipModel,
    EnterpriseAssetModel,
)
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
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
        seed_enterprise_estate(session)
        session.commit()

    yield engine
    engine.dispose()


def _service(asset_key: str) -> CanonicalAssetRef:
    return CanonicalAssetRef(asset_key=asset_key, asset_type=AssetType.SERVICE)


def _persist_candidate(
    session: Session,
    *,
    asset_key: str,
    asset_type: AssetType,
    candidate_id: UUID | None = None,
) -> Candidate:
    timestamp = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="candidate-dependency-context-test",
        source_reference=f"dependency-context-{uuid4()}",
        captured_at=timestamp,
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="candidate-dependency-context-test",
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
        candidate_id=candidate_id or uuid4(),
        signal_ids=frozenset({signal.signal_id}),
        evidence_ids=frozenset({evidence.evidence_id}),
        canonical_asset=signal.affected_asset,
        hypothesis="Potential missing request timeout",
        correlation_rationale="One exact canonical asset and problem family.",
    )
    persist_candidate(session, candidate)
    return candidate


def _add_asset(session: Session, asset_key: str, asset_type: AssetType) -> None:
    session.add(
        EnterpriseAssetModel(
            asset_key=asset_key,
            asset_type=asset_type.value,
            name=f"Synthetic {asset_key}",
            criticality=AssetCriticality.LOW.value,
            lifecycle_status=AssetLifecycleStatus.ACTIVE.value,
        )
    )
    session.flush()


def _add_relationship(
    session: Session,
    source_asset_key: str,
    target_asset_key: str,
    relationship_type: AssetRelationshipType,
) -> None:
    source_asset = (
        session.query(EnterpriseAssetModel).filter_by(asset_key=source_asset_key).one()
    )
    target_asset = (
        session.query(EnterpriseAssetModel).filter_by(asset_key=target_asset_key).one()
    )
    session.add(
        AssetRelationshipModel(
            source_asset=source_asset,
            target_asset=target_asset,
            relationship_type=relationship_type.value,
        )
    )
    session.flush()


def test_candidate_not_found_returns_none(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        assert load_candidate_dependency_context(session, uuid4()) is None


def test_service_anchor_preserves_dependency_direction_and_seeded_blast_radius(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        orbit_candidate = _persist_candidate(
            session,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            candidate_id=UUID("00000000-0000-0000-0000-000000000901"),
        )
        first = load_candidate_dependency_context(
            session,
            orbit_candidate.candidate_id,
        )
        repeated = load_candidate_dependency_context(
            session,
            orbit_candidate.candidate_id,
        )

        consumer_candidate = _persist_candidate(
            session,
            asset_key="svc-asteria-editor",
            asset_type=AssetType.SERVICE,
        )
        consumer_context = load_candidate_dependency_context(
            session,
            consumer_candidate.candidate_id,
        )

    assert first == repeated
    assert first is not None
    assert first.candidate_asset == _service("svc-orbit-catalog")
    assert first.dependency_anchors == (_service("svc-orbit-catalog"),)
    assert first.direct_dependencies == ()
    assert first.direct_dependents == (
        _service("svc-asteria-editor"),
        _service("svc-borealis-renderer"),
    )
    assert first.reachable_dependents == first.direct_dependents

    assert consumer_context is not None
    assert consumer_context.direct_dependencies == (_service("svc-orbit-catalog"),)
    assert consumer_context.direct_dependents == ()
    assert consumer_context.reachable_dependents == ()


def test_repository_uses_incoming_implemented_by_and_matches_service_context(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
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
        service_context = load_candidate_dependency_context(
            session,
            service_candidate.candidate_id,
        )
        repository_context = load_candidate_dependency_context(
            session,
            repository_candidate.candidate_id,
        )

    assert service_context is not None
    assert repository_context is not None
    assert repository_context.candidate_asset == CanonicalAssetRef(
        asset_key="repo-orbit-catalog",
        asset_type=AssetType.REPOSITORY,
    )
    assert repository_context.dependency_anchors == (_service("svc-orbit-catalog"),)
    assert repository_context.direct_dependencies == service_context.direct_dependencies
    assert repository_context.direct_dependents == service_context.direct_dependents
    assert (
        repository_context.reachable_dependents == service_context.reachable_dependents
    )


def test_application_uses_outgoing_contains_and_deduplicates_multiple_anchors(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="app-asteria-canvas",
            asset_type=AssetType.APPLICATION,
        )
        context = load_candidate_dependency_context(session, candidate.candidate_id)

    assert context is not None
    assert context.dependency_anchors == (
        _service("svc-asteria-editor"),
        _service("svc-orbit-catalog"),
    )
    assert context.direct_dependencies == (_service("svc-orbit-catalog"),)
    assert context.direct_dependents == (
        _service("svc-asteria-editor"),
        _service("svc-borealis-renderer"),
    )
    assert context.reachable_dependents == (_service("svc-borealis-renderer"),)


def test_anchor_resolution_is_one_hop_and_structural_edges_are_not_dependencies(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        _add_asset(session, "app-one-hop", AssetType.APPLICATION)
        _add_asset(session, "svc-one-hop", AssetType.SERVICE)
        _add_asset(session, "svc-nested", AssetType.SERVICE)
        _add_asset(session, "repo-one-hop", AssetType.REPOSITORY)
        _add_relationship(
            session,
            "app-one-hop",
            "svc-one-hop",
            AssetRelationshipType.CONTAINS,
        )
        _add_relationship(
            session,
            "svc-one-hop",
            "svc-nested",
            AssetRelationshipType.CONTAINS,
        )
        _add_relationship(
            session,
            "svc-one-hop",
            "repo-one-hop",
            AssetRelationshipType.IMPLEMENTED_BY,
        )
        candidate = _persist_candidate(
            session,
            asset_key="app-one-hop",
            asset_type=AssetType.APPLICATION,
        )
        context = load_candidate_dependency_context(session, candidate.candidate_id)

    assert context is not None
    assert context.dependency_anchors == (_service("svc-one-hop"),)
    assert context.direct_dependencies == ()
    assert context.direct_dependents == ()
    assert context.reachable_dependents == ()


def test_repository_without_service_anchor_has_empty_dependency_context(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        _add_asset(session, "repo-unlinked", AssetType.REPOSITORY)
        candidate = _persist_candidate(
            session,
            asset_key="repo-unlinked",
            asset_type=AssetType.REPOSITORY,
        )
        context = load_candidate_dependency_context(session, candidate.candidate_id)

    assert context is not None
    assert context.dependency_anchors == ()
    assert context.direct_dependencies == ()
    assert context.direct_dependents == ()
    assert context.reachable_dependents == ()


def test_dependency_cycle_terminates_deduplicates_and_excludes_starting_anchor(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        for asset_key in ("svc-cycle-a", "svc-cycle-b", "svc-cycle-c"):
            _add_asset(session, asset_key, AssetType.SERVICE)
        for source_asset_key, target_asset_key in (
            ("svc-cycle-a", "svc-cycle-b"),
            ("svc-cycle-b", "svc-cycle-c"),
            ("svc-cycle-c", "svc-cycle-a"),
        ):
            _add_relationship(
                session,
                source_asset_key,
                target_asset_key,
                AssetRelationshipType.DEPENDS_ON,
            )
        candidate = _persist_candidate(
            session,
            asset_key="svc-cycle-a",
            asset_type=AssetType.SERVICE,
        )
        context = load_candidate_dependency_context(session, candidate.candidate_id)

    assert context is not None
    assert context.direct_dependencies == (_service("svc-cycle-b"),)
    assert context.direct_dependents == (_service("svc-cycle-c"),)
    assert context.reachable_dependents == (
        _service("svc-cycle-b"),
        _service("svc-cycle-c"),
    )
    assert _service("svc-cycle-a") not in context.reachable_dependents


def test_projection_is_frozen_ordered_and_has_no_governance_or_impact_claims(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        )
        context = load_candidate_dependency_context(session, candidate.candidate_id)

    assert context is not None
    assert [asset.asset_key for asset in context.direct_dependents] == sorted(
        asset.asset_key for asset in context.direct_dependents
    )
    assert {field.name for field in fields(CandidateDependencyContext)} == {
        "candidate_id",
        "candidate_asset",
        "dependency_anchors",
        "direct_dependencies",
        "direct_dependents",
        "reachable_dependents",
    }
    assert {
        "risk",
        "effort",
        "priority",
        "severity",
        "impact",
        "validation",
        "technical_debt",
        "ground_truth",
    }.isdisjoint(field.name for field in fields(CandidateDependencyContext))
    with pytest.raises(FrozenInstanceError):
        context.candidate_id = uuid4()  # type: ignore[misc]


def test_broken_candidate_asset_integrity_raises_explicit_error(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="repo-orbit-catalog",
            asset_type=AssetType.REPOSITORY,
        )
        session.commit()

    with database_engine.begin() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(
            update(CandidateModel)
            .where(CandidateModel.candidate_id == candidate.candidate_id)
            .values(canonical_asset_id=999_999)
        )

    with Session(database_engine) as session:
        with pytest.raises(
            CandidateDependencyContextIntegrityError,
            match="canonical enterprise asset is missing",
        ):
            load_candidate_dependency_context(session, candidate.candidate_id)


def test_loader_executes_only_selects_without_flush_commit_or_mutation(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        )
        session.commit()
        statements: list[str] = []
        flush_count = 0
        commit_count = 0

        def record_statement(
            _connection: object,
            _cursor: object,
            statement: str,
            _parameters: object,
            _context: object,
            _executemany: bool,
        ) -> None:
            statements.append(statement)

        def record_flush(
            _session: Session,
            _context: object,
            _instances: object,
        ) -> None:
            nonlocal flush_count
            flush_count += 1

        def record_commit(_session: Session) -> None:
            nonlocal commit_count
            commit_count += 1

        event.listen(database_engine, "before_cursor_execute", record_statement)
        event.listen(session, "before_flush", record_flush)
        event.listen(session, "before_commit", record_commit)
        try:
            context = load_candidate_dependency_context(
                session,
                candidate.candidate_id,
            )
        finally:
            event.remove(database_engine, "before_cursor_execute", record_statement)

        assert context is not None
        assert statements
        assert all(
            statement.lstrip().upper().startswith("SELECT") for statement in statements
        )
        assert flush_count == 0
        assert commit_count == 0
        assert not session.new
        assert not session.dirty
        assert not session.deleted


def test_runtime_boundary_has_no_ground_truth_or_governance_dependency() -> None:
    source = inspect.getsource(
        importlib.import_module(
            "app.infrastructure.database.candidate_dependency_context"
        )
    ).lower()

    assert "ground_truth" not in source
    assert "technicaldebt" not in source
    assert "evaluation" not in source
    assert "commit(" not in source
