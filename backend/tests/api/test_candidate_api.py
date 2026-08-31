from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, func, select, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/candidates"
BASE_TIME = datetime(2026, 8, 31, 9, 0, tzinfo=UTC)


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    backend_root = Path(__file__).resolve().parents[2]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        operations = Operations(context)
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        seed_enterprise_estate(session)
        session.execute(
            text(
                "UPDATE incidents SET started_at = started_at || '+00:00' "
                "WHERE instr(started_at, '+') = 0"
            )
        )
        session.execute(
            text(
                "UPDATE incidents SET resolved_at = resolved_at || '+00:00' "
                "WHERE resolved_at IS NOT NULL AND instr(resolved_at, '+') = 0"
            )
        )
        session.commit()

    yield engine
    engine.dispose()


@pytest.fixture
def client(database_engine: Engine) -> Iterator[TestClient]:
    def override_database_session() -> Iterator[Session]:
        with Session(database_engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _persist_signal(
    session: Session,
    *,
    signal_id: str,
    evidence_id: str,
    source_record_id: str,
    asset_key: str,
    asset_type: AssetType,
    detected_at: datetime,
) -> NormalizedSignal:
    evidence = Evidence(
        evidence_id=UUID(evidence_id),
        source_system="candidate-api-test",
        source_reference=f"evidence:{source_record_id}",
        captured_at=detected_at + timedelta(minutes=1),
        reference_uri=f"https://synthetic.invalid/{source_record_id}",
    )
    signal = Signal(
        signal_id=UUID(signal_id),
        source_system="candidate-api-test",
        source_record_id=source_record_id,
        detected_at=detected_at,
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    normalized = NormalizedSignal(signal=signal, evidence=frozenset({evidence}))
    persist_normalized_signal(session, normalized)
    return normalized


def _persist_candidate(
    session: Session,
    *,
    candidate_id: str,
    asset_key: str,
    asset_type: AssetType,
    hypothesis: str,
    signals: tuple[NormalizedSignal, ...],
) -> Candidate:
    candidate = Candidate(
        candidate_id=UUID(candidate_id),
        signal_ids=frozenset(item.signal.signal_id for item in signals),
        evidence_ids=frozenset(
            evidence_id for item in signals for evidence_id in item.signal.evidence_ids
        ),
        canonical_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        hypothesis=hypothesis,
        correlation_rationale="Exact canonical asset and deterministic problem family.",
    )
    persist_candidate(session, candidate)
    return candidate


def _candidate_with_one_signal(
    session: Session,
    *,
    suffix: int,
    asset_key: str = "svc-orbit-catalog",
    asset_type: AssetType = AssetType.SERVICE,
    hypothesis: str = "Potential missing request timeout",
) -> Candidate:
    signal = _persist_signal(
        session,
        signal_id=f"00000000-0000-0000-0000-{suffix:012d}",
        evidence_id=f"10000000-0000-0000-0000-{suffix:012d}",
        source_record_id=f"source-{suffix}",
        asset_key=asset_key,
        asset_type=asset_type,
        detected_at=BASE_TIME + timedelta(minutes=suffix),
    )
    return _persist_candidate(
        session,
        candidate_id=f"20000000-0000-0000-0000-{suffix:012d}",
        asset_key=asset_key,
        asset_type=asset_type,
        hypothesis=hypothesis,
        signals=(signal,),
    )


def test_empty_candidate_list_returns_deterministic_empty_response(
    client: TestClient,
) -> None:
    first = client.get(API_PATH)
    repeated = client.get(API_PATH)

    assert first.status_code == 200
    assert first.json() == {"items": [], "count": 0}
    assert repeated.json() == first.json()


def test_candidate_list_is_ordered_and_exposes_small_factual_summaries(
    client: TestClient,
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        later_service = _candidate_with_one_signal(
            session,
            suffix=3,
            hypothesis="Zulu hypothesis",
        )
        repository = _candidate_with_one_signal(
            session,
            suffix=2,
            asset_key="repo-orbit-catalog",
            asset_type=AssetType.REPOSITORY,
        )
        earlier_service = _candidate_with_one_signal(
            session,
            suffix=1,
            hypothesis="Alpha hypothesis",
        )
        session.commit()

    response = client.get(API_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 3
    assert [item["candidate_id"] for item in body["items"]] == [
        str(repository.candidate_id),
        str(earlier_service.candidate_id),
        str(later_service.candidate_id),
    ]
    assert body["items"][0] == {
        "candidate_id": str(repository.candidate_id),
        "hypothesis": repository.hypothesis,
        "canonical_asset": {
            "asset_key": "repo-orbit-catalog",
            "asset_type": "REPOSITORY",
        },
        "enterprise_asset": {
            "asset_key": "repo-orbit-catalog",
            "asset_type": "REPOSITORY",
            "name": "Orbit Catalog Repository",
            "criticality": "MEDIUM",
            "lifecycle_status": "ACTIVE",
        },
        "signal_count": 1,
        "evidence_count": 1,
    }
    forbidden_fields = {
        "risk",
        "effort",
        "priority",
        "review_status",
        "validation",
        "technical_debt",
        "suggested_owner",
        "recommended_owner",
        "confidence",
    }
    serialized_body = str(body).lower()
    assert all(field not in serialized_body for field in forbidden_fields)


def test_candidate_detail_has_exact_membership_provenance_and_context(
    client: TestClient,
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        later = _persist_signal(
            session,
            signal_id="00000000-0000-0000-0000-000000000012",
            evidence_id="10000000-0000-0000-0000-000000000012",
            source_record_id="member-later",
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            detected_at=BASE_TIME + timedelta(hours=2),
        )
        earlier = _persist_signal(
            session,
            signal_id="00000000-0000-0000-0000-000000000011",
            evidence_id="10000000-0000-0000-0000-000000000011",
            source_record_id="member-earlier",
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            detected_at=BASE_TIME + timedelta(hours=1),
        )
        unrelated = _persist_signal(
            session,
            signal_id="00000000-0000-0000-0000-000000000010",
            evidence_id="10000000-0000-0000-0000-000000000010",
            source_record_id="unrelated-same-asset",
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            detected_at=BASE_TIME,
        )
        candidate = _persist_candidate(
            session,
            candidate_id="20000000-0000-0000-0000-000000000001",
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            hypothesis="Potential missing request timeout",
            signals=(later, earlier),
        )
        session.commit()

    first = client.get(f"{API_PATH}/{candidate.candidate_id}")
    repeated = client.get(f"{API_PATH}/{candidate.candidate_id}")

    assert first.status_code == 200
    assert repeated.json() == first.json()
    body = first.json()
    assert body["candidate"] == {
        "candidate_id": str(candidate.candidate_id),
        "signal_ids": sorted(str(item) for item in candidate.signal_ids),
        "evidence_ids": sorted(str(item) for item in candidate.evidence_ids),
        "canonical_asset": {
            "asset_key": "svc-orbit-catalog",
            "asset_type": "SERVICE",
        },
        "hypothesis": candidate.hypothesis,
        "correlation_rationale": candidate.correlation_rationale,
    }
    assert [item["signal_id"] for item in body["signals"]] == [
        str(earlier.signal.signal_id),
        str(later.signal.signal_id),
    ]
    assert str(unrelated.signal.signal_id) not in str(body["signals"])
    assert [item["evidence_id"] for item in body["evidence"]] == [
        str(next(iter(earlier.evidence)).evidence_id),
        str(next(iter(later.evidence)).evidence_id),
    ]
    assert body["evidence"][0]["source_system"] == "candidate-api-test"
    assert body["evidence"][0]["source_reference"] == "evidence:member-earlier"
    assert body["evidence"][0]["reference_uri"].endswith("/member-earlier")

    enterprise = body["enterprise_context"]
    assert enterprise["enterprise_asset"]["criticality"] == "HIGH"
    assert enterprise["enterprise_ownerships"] == [
        {
            "asset_ownership": {
                "asset_key": "svc-orbit-catalog",
                "team_key": "team-orbit",
                "ownership_role": "PRIMARY",
            },
            "team": {"team_key": "team-orbit", "name": "Orbit Platform Team"},
        }
    ]
    assert all(
        relationship["source_asset_key"] == "svc-orbit-catalog"
        or relationship["target_asset_key"] == "svc-orbit-catalog"
        for relationship in enterprise["direct_relationships"]
    )
    assert {item["incident_key"] for item in enterprise["direct_incidents"]} == {
        "inc-orbit-001",
        "inc-orbit-002",
        "inc-orbit-003",
    }

    dependency = body["dependency_context"]
    assert dependency["dependency_anchors"] == [
        {"asset_key": "svc-orbit-catalog", "asset_type": "SERVICE"}
    ]
    assert [item["asset_key"] for item in dependency["direct_dependents"]] == [
        "svc-asteria-editor",
        "svc-borealis-renderer",
    ]
    assert dependency["reachable_dependents"] == dependency["direct_dependents"]
    assert all(
        field not in str(dependency).lower()
        for field in ("risk_score", "impact_score", "will_fail")
    )


def test_candidate_not_found_and_malformed_uuid_contract(client: TestClient) -> None:
    unknown = client.get(f"{API_PATH}/30000000-0000-0000-0000-000000000001")
    malformed = client.get(f"{API_PATH}/not-a-uuid")

    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "Candidate not found"}
    assert malformed.status_code == 422


def test_broken_enterprise_integrity_returns_generic_500(
    client: TestClient,
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _candidate_with_one_signal(session, suffix=21)
        session.commit()

    with database_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA ignore_check_constraints=ON")
        connection.execute(
            text(
                "UPDATE enterprise_assets SET asset_type = 'INVALID' "
                "WHERE asset_key = 'svc-orbit-catalog'"
            )
        )
        connection.commit()
        connection.exec_driver_sql("PRAGMA ignore_check_constraints=OFF")

    response = client.get(f"{API_PATH}/{candidate.candidate_id}")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Persisted Candidate data failed integrity validation"
    }
    assert "enterprise_assets" not in response.text
    assert "select" not in response.text.lower()


def test_broken_signal_membership_returns_generic_500(
    client: TestClient,
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        candidate = _candidate_with_one_signal(session, suffix=22)
        session.commit()

    with database_engine.connect() as connection:
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.execute(
            CandidateSignalModel.__table__.insert().values(
                candidate_id=candidate.candidate_id,
                signal_id=UUID("40000000-0000-0000-0000-000000000001"),
            )
        )
        connection.commit()
        connection.exec_driver_sql("PRAGMA foreign_keys=ON")

    response = client.get(f"{API_PATH}/{candidate.candidate_id}")

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Persisted Candidate data failed integrity validation"
    }


def test_get_read_path_does_not_flush_commit_or_mutate(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as setup_session:
        candidate = _candidate_with_one_signal(setup_session, suffix=31)
        setup_session.commit()

    session = Session(database_engine)
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

    def override_database_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_database_session] = override_database_session
    try:
        with TestClient(app) as test_client:
            list_response = test_client.get(API_PATH)
            detail_response = test_client.get(f"{API_PATH}/{candidate.candidate_id}")
    finally:
        app.dependency_overrides.clear()
        session.close()

    assert list_response.status_code == 200
    assert detail_response.status_code == 200
    assert flushes == 0
    assert commits == 0
    with Session(database_engine) as verification_session:
        assert (
            verification_session.scalar(
                select(func.count()).select_from(CandidateModel)
            )
            == 1
        )
        assert (
            verification_session.scalar(select(func.count()).select_from(SignalModel))
            == 1
        )
        assert (
            verification_session.scalar(select(func.count()).select_from(EvidenceModel))
            == 1
        )
