from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import (
    AppliedHumanValidation,
    apply_human_validation,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.main import app
from app.signal_ingestion import NormalizedSignal

API_PATH = "/api/v1/technical-debts"
POC_ACTOR = HumanActorContext(actor_reference="poc:local-reviewer")
BASE_TIME = datetime(2026, 9, 6, 19, 0, tzinfo=UTC)
FORBIDDEN_FIELDS = (
    "risk",
    "effort",
    "priority",
    "validated_owner",
    "target_date",
    "suggested_owner",
    "recommended_owner",
)


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
        operations = Operations(MigrationContext.configure(connection))
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


def _persist_candidate(
    engine: Engine,
    *,
    suffix: int,
    asset_key: str,
    asset_type: AssetType,
    hypothesis: str,
) -> Candidate:
    evidence = Evidence(
        evidence_id=UUID(f"10000000-0000-0000-0000-{suffix:012d}"),
        source_system="technical-debt-api-test",
        source_reference=f"evidence-{suffix}",
        captured_at=BASE_TIME + timedelta(minutes=suffix),
        reference_uri=f"https://synthetic.invalid/{suffix}",
    )
    signal = Signal(
        signal_id=UUID(f"00000000-0000-0000-0000-{suffix:012d}"),
        source_system="technical-debt-api-test",
        source_record_id=f"source-{suffix}",
        detected_at=BASE_TIME + timedelta(minutes=suffix),
        signal_type="MISSING_TIMEOUT",
        affected_asset=CanonicalAssetRef(asset_key=asset_key, asset_type=asset_type),
        severity="MEDIUM",
        evidence_ids=frozenset({evidence.evidence_id}),
    )
    candidate = Candidate(
        candidate_id=UUID(f"20000000-0000-0000-0000-{suffix:012d}"),
        signal_ids=frozenset({signal.signal_id}),
        evidence_ids=frozenset({evidence.evidence_id}),
        canonical_asset=signal.affected_asset,
        hypothesis=hypothesis,
        correlation_rationale="Exact canonical asset and deterministic problem family.",
    )
    with Session(engine) as session:
        persist_normalized_signal(
            session,
            NormalizedSignal(signal=signal, evidence=frozenset({evidence})),
        )
        persist_candidate(session, candidate)
        session.commit()
    return candidate


def _validate(
    engine: Engine,
    candidate: Candidate,
    created_at: datetime,
) -> AppliedHumanValidation:
    with Session(engine) as session:
        return apply_human_validation(
            session,
            HumanValidationCommand(
                candidate_id=candidate.candidate_id,
                decision=HumanDecisionType.VALIDATE,
                expected_governance_revision=0,
                rationale="The Candidate is a validated structural issue.",
            ),
            POC_ACTOR,
            clock=lambda: created_at,
        )


def test_empty_technical_debt_list(client: TestClient) -> None:
    first = client.get(API_PATH)
    repeated = client.get(API_PATH)

    assert first.status_code == 200
    assert first.json() == {"items": [], "count": 0}
    assert repeated.json() == first.json()


def test_technical_debt_list_is_ordered_and_projects_candidate_facts(
    client: TestClient,
    database_engine: Engine,
) -> None:
    later_candidate = _persist_candidate(
        database_engine,
        suffix=2,
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
        hypothesis="Zulu hypothesis",
    )
    earlier_candidate = _persist_candidate(
        database_engine,
        suffix=1,
        asset_key="repo-orbit-catalog",
        asset_type=AssetType.REPOSITORY,
        hypothesis="Alpha hypothesis",
    )
    later = _validate(
        database_engine,
        later_candidate,
        datetime(2026, 9, 6, 19, 2, tzinfo=UTC),
    )
    earlier = _validate(
        database_engine,
        earlier_candidate,
        datetime(2026, 9, 6, 19, 1, tzinfo=UTC),
    )

    response = client.get(API_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 2
    assert [item["technical_debt_id"] for item in body["items"]] == [
        str(earlier.technical_debt.technical_debt_id),
        str(later.technical_debt.technical_debt_id),
    ]
    assert earlier.technical_debt is not None
    assert later.technical_debt is not None
    assert body["items"][0]["technical_debt_id"] == str(
        earlier.technical_debt.technical_debt_id
    )
    assert body["items"][0]["lifecycle_status"] == "REGISTERED"
    assert body["items"][0]["source_candidate_id"] == str(
        earlier_candidate.candidate_id
    )
    assert body["items"][0]["hypothesis"] == "Alpha hypothesis"
    assert body["items"][0]["canonical_asset"] == {
        "asset_key": "repo-orbit-catalog",
        "asset_type": "REPOSITORY",
    }
    assert "action_proposals" not in body["items"][0]
    assert datetime.fromisoformat(
        body["items"][0]["created_at"].replace("Z", "+00:00")
    ) == datetime(2026, 9, 6, 19, 1, tzinfo=UTC)
    serialized = str(body).lower()
    assert all(field not in serialized for field in FORBIDDEN_FIELDS)


def test_technical_debt_detail_exposes_candidate_and_decision_provenance(
    client: TestClient,
    database_engine: Engine,
) -> None:
    candidate = _persist_candidate(
        database_engine,
        suffix=3,
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
        hypothesis="Potential missing request timeout",
    )
    created = _validate(
        database_engine,
        candidate,
        datetime(2026, 9, 6, 19, 3, tzinfo=UTC),
    )
    assert created.technical_debt is not None

    response = client.get(f"{API_PATH}/{created.technical_debt.technical_debt_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["technical_debt_id"] == str(created.technical_debt.technical_debt_id)
    assert body["lifecycle_status"] == "REGISTERED"
    assert body["source_candidate"] == {
        "candidate_id": str(candidate.candidate_id),
        "hypothesis": candidate.hypothesis,
        "correlation_rationale": candidate.correlation_rationale,
        "canonical_asset": {
            "asset_key": "svc-orbit-catalog",
            "asset_type": "SERVICE",
        },
    }
    assert body["creation_human_decision"]["human_decision_id"] == str(
        created.human_decision.human_decision_id
    )
    assert body["creation_human_decision"]["decision"] == "VALIDATE"
    assert body["creation_human_decision"]["sequence_number"] == 1
    assert body["creation_human_decision"]["rationale"] == (
        created.human_decision.rationale
    )
    assert body["creation_human_decision"]["actor_reference"] == (
        POC_ACTOR.actor_reference
    )
    assert datetime.fromisoformat(
        body["creation_human_decision"]["created_at"].replace("Z", "+00:00")
    ) == datetime(2026, 9, 6, 19, 3, tzinfo=UTC)
    assert body["action_proposals"] == []
    serialized = str(body).lower()
    assert all(field not in serialized for field in FORBIDDEN_FIELDS)


def test_unknown_and_malformed_technical_debt_id_contract(client: TestClient) -> None:
    unknown = client.get(f"{API_PATH}/{uuid4()}")
    malformed = client.get(f"{API_PATH}/not-a-uuid")

    assert unknown.status_code == 404
    assert unknown.json() == {"detail": "TechnicalDebt not found"}
    assert malformed.status_code == 422
