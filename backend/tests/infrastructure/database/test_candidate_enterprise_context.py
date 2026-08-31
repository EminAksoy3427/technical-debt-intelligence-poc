from collections.abc import Iterator
from dataclasses import fields
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, text, update
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_enterprise_context import CandidateEnterpriseContext
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationship,
    AssetRelationshipType,
    AssetType,
    EnterpriseAsset,
    OwnershipRole,
)
from app.domain.signals import Evidence, Signal
from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
)
from app.infrastructure.database.candidate_enterprise_context import (
    CandidateEnterpriseContextIntegrityError,
    load_candidate_enterprise_context,
)
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
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
        session.flush()
        # SQLite drops timezone offsets from DateTime bindings. Preserve the
        # synthetic UTC offsets so these tests exercise the Incident invariant.
        for incident in SYNTHETIC_INCIDENTS:
            session.execute(
                text(
                    "UPDATE incidents "
                    "SET started_at = :started_at, resolved_at = :resolved_at "
                    "WHERE incident_key = :incident_key"
                ),
                {
                    "incident_key": incident.incident_key,
                    "started_at": incident.started_at.isoformat(),
                    "resolved_at": (
                        incident.resolved_at.isoformat()
                        if incident.resolved_at is not None
                        else None
                    ),
                },
            )
        session.commit()

    yield engine
    engine.dispose()


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
        source_system="candidate-context-test",
        source_reference=f"context-{uuid4()}",
        captured_at=timestamp,
    )
    signal = Signal(
        signal_id=uuid4(),
        source_system="candidate-context-test",
        source_record_id=f"context-{uuid4()}",
        detected_at=timestamp,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(
            asset_key=asset_key,
            asset_type=asset_type,
        ),
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


def test_loads_exact_factual_context_with_direct_topology_and_incidents(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            candidate_id=UUID("00000000-0000-0000-0000-000000000801"),
        )
        context = load_candidate_enterprise_context(session, candidate.candidate_id)

    assert context is not None
    assert context.candidate_id == candidate.candidate_id
    assert context.enterprise_asset == next(
        asset
        for asset in SYNTHETIC_ENTERPRISE_ASSETS
        if asset.asset_key == candidate.canonical_asset.asset_key
    )
    assert context.enterprise_asset.criticality is AssetCriticality.HIGH
    assert context.enterprise_asset.lifecycle_status is AssetLifecycleStatus.ACTIVE
    assert [
        (
            item.asset_ownership.ownership_role,
            item.asset_ownership.team_key,
            item.team.name,
        )
        for item in context.enterprise_ownerships
    ] == [(OwnershipRole.PRIMARY, "team-orbit", "Orbit Platform Team")]
    assert context.direct_relationships == (
        AssetRelationship(
            "app-asteria-canvas",
            "svc-orbit-catalog",
            AssetRelationshipType.CONTAINS,
        ),
        AssetRelationship(
            "svc-asteria-editor",
            "svc-orbit-catalog",
            AssetRelationshipType.DEPENDS_ON,
        ),
        AssetRelationship(
            "svc-borealis-renderer",
            "svc-orbit-catalog",
            AssetRelationshipType.DEPENDS_ON,
        ),
        AssetRelationship(
            "svc-orbit-catalog",
            "repo-orbit-catalog",
            AssetRelationshipType.IMPLEMENTED_BY,
        ),
    )
    assert context.direct_incidents == tuple(
        sorted(
            (
                incident
                for incident in SYNTHETIC_INCIDENTS
                if incident.primary_affected_asset_key == "svc-orbit-catalog"
            ),
            key=lambda item: (item.started_at, item.incident_key),
        )
    )
    assert "inc-asteria-001" not in {
        incident.incident_key for incident in context.direct_incidents
    }


def test_context_is_deterministic_direct_only_and_has_no_governance_derivations(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
        )
        first = load_candidate_enterprise_context(session, candidate.candidate_id)
        repeated = load_candidate_enterprise_context(session, candidate.candidate_id)

    assert first == repeated
    assert first is not None
    assert "repo-asteria-editor" not in {
        relationship.source_asset_key for relationship in first.direct_relationships
    } | {relationship.target_asset_key for relationship in first.direct_relationships}
    context_fields = {field.name for field in fields(CandidateEnterpriseContext)}
    assert context_fields == {
        "candidate_id",
        "enterprise_asset",
        "enterprise_ownerships",
        "direct_relationships",
        "direct_incidents",
    }
    assert {
        "risk",
        "effort",
        "priority",
        "severity",
        "blast_radius",
        "validation",
        "technical_debt_owner",
        "suggested_debt_owner",
        "recommended_owner",
    }.isdisjoint(context_fields)


def test_exact_asset_without_direct_incidents_has_empty_incident_history(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _persist_candidate(
            session,
            asset_key="repo-orbit-catalog",
            asset_type=AssetType.REPOSITORY,
        )
        context = load_candidate_enterprise_context(session, candidate.candidate_id)

    assert context is not None
    assert context.direct_incidents == ()
    assert context.direct_relationships == (
        AssetRelationship(
            "svc-orbit-catalog",
            "repo-orbit-catalog",
            AssetRelationshipType.IMPLEMENTED_BY,
        ),
    )


def test_asset_without_ownership_returns_empty_enterprise_ownerships(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        session.add(
            EnterpriseAssetModel(
                asset_key="repo-unowned-context",
                asset_type=AssetType.REPOSITORY.value,
                name="Unowned Context Repository",
                criticality=AssetCriticality.LOW.value,
                lifecycle_status=AssetLifecycleStatus.PLANNED.value,
            )
        )
        session.flush()
        candidate = _persist_candidate(
            session,
            asset_key="repo-unowned-context",
            asset_type=AssetType.REPOSITORY,
        )
        context = load_candidate_enterprise_context(session, candidate.candidate_id)

    assert context is not None
    assert context.enterprise_asset == EnterpriseAsset(
        asset_key="repo-unowned-context",
        asset_type=AssetType.REPOSITORY,
        name="Unowned Context Repository",
        criticality=AssetCriticality.LOW,
        lifecycle_status=AssetLifecycleStatus.PLANNED,
    )
    assert context.enterprise_ownerships == ()
    assert context.direct_relationships == ()
    assert context.direct_incidents == ()


def test_candidate_not_found_returns_none(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        assert load_candidate_enterprise_context(session, uuid4()) is None


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
            CandidateEnterpriseContextIntegrityError,
            match="canonical enterprise asset is missing",
        ):
            load_candidate_enterprise_context(session, candidate.candidate_id)


def test_context_loading_executes_selects_without_flush_commit_or_mutation(
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
            context = load_candidate_enterprise_context(
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
