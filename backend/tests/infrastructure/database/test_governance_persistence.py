from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.dialects import mssql, sqlite
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.human_decision_persistence import (
    candidate_governance_boundary_statement,
    load_human_decision,
    load_human_decision_history,
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_persistence import (
    load_technical_debt,
    persist_technical_debt,
)

CREATED_AT = datetime(2026, 9, 6, 17, 0, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000711")
SECOND_CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000712")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")


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
        operations = Operations(MigrationContext.configure(connection))
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        _seed_candidate(session, CANDIDATE_ID, "source-711")
        _seed_candidate(session, SECOND_CANDIDATE_ID, "source-712")
        session.commit()

    yield engine
    engine.dispose()


def _seed_candidate(
    session: Session,
    candidate_id: UUID,
    source_record_id: str,
) -> None:
    asset = session.scalar(
        select(EnterpriseAssetModel).where(
            EnterpriseAssetModel.asset_key == "repo-borealis-renderer"
        )
    )
    if asset is None:
        asset = EnterpriseAssetModel(
            asset_key="repo-borealis-renderer",
            asset_type="REPOSITORY",
            name="Borealis Renderer Repository",
            criticality="MEDIUM",
            lifecycle_status="ACTIVE",
        )
    signal = SignalModel(
        signal_id=uuid4(),
        source_system="governance-persistence-test",
        source_record_id=source_record_id,
        detected_at=CREATED_AT,
        signal_type="MISSING_TIMEOUT",
        affected_asset=asset,
        severity="MEDIUM",
        evidence=[
            EvidenceModel(
                evidence_id=uuid4(),
                source_system="governance-persistence-test",
                source_reference=source_record_id,
                captured_at=CREATED_AT,
            )
        ],
    )
    session.add(
        CandidateModel(
            candidate_id=candidate_id,
            canonical_asset=asset,
            hypothesis="Potential missing request timeout",
            correlation_rationale=(
                "Persisted Signals share an asset and problem family."
            ),
            signal_memberships=[CandidateSignalModel(signal=signal)],
        )
    )


def _human_decision(
    *,
    human_decision_id: UUID = DECISION_ID,
    candidate_id: UUID = CANDIDATE_ID,
    sequence_number: int = 1,
    decision_type: HumanDecisionType = HumanDecisionType.VALIDATE,
    created_at: datetime | None = None,
) -> HumanDecision:
    if decision_type is HumanDecisionType.REQUEST_INFO:
        rationale = None
        requested_information = "Who owns the renderer service?"
    else:
        rationale = "The Candidate is a validated structural issue."
        requested_information = None
    return HumanDecision(
        human_decision_id=human_decision_id,
        candidate_id=candidate_id,
        sequence_number=sequence_number,
        decision_type=decision_type,
        rationale=rationale,
        requested_information=requested_information,
        actor_reference="poc:local-reviewer",
        created_at=CREATED_AT if created_at is None else created_at,
    )


def _technical_debt(
    *,
    technical_debt_id: UUID = DEBT_ID,
    source_candidate_id: UUID = CANDIDATE_ID,
    creation_human_decision_id: UUID = DECISION_ID,
) -> TechnicalDebt:
    return TechnicalDebt(
        technical_debt_id=technical_debt_id,
        source_candidate_id=source_candidate_id,
        creation_human_decision_id=creation_human_decision_id,
        lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
        created_at=CREATED_AT,
    )


def test_human_decision_round_trips_timezone_aware_domain_contract(
    database_engine: Engine,
) -> None:
    decision = _human_decision()
    with Session(database_engine) as session:
        persist_human_decision(session, decision)
        session.commit()

    with Session(database_engine) as session:
        loaded = load_human_decision(session, DECISION_ID)
        assert loaded == decision
        assert loaded is not None
        assert loaded.created_at.tzinfo is not None
        assert loaded.created_at.utcoffset() is not None


def test_human_decision_history_is_ordered_by_sequence_number(
    database_engine: Engine,
) -> None:
    later = _human_decision(
        human_decision_id=uuid4(),
        sequence_number=2,
        decision_type=HumanDecisionType.VALIDATE,
        created_at=CREATED_AT + timedelta(minutes=5),
    )
    earlier = _human_decision(
        human_decision_id=uuid4(),
        sequence_number=1,
        decision_type=HumanDecisionType.REQUEST_INFO,
    )
    with Session(database_engine) as session:
        persist_human_decision(session, later)
        persist_human_decision(session, earlier)
        session.commit()

    with Session(database_engine) as session:
        history = load_human_decision_history(session, CANDIDATE_ID)
        assert [item.sequence_number for item in history] == [1, 2]
        assert history == (earlier, later)


def test_technical_debt_round_trips_registered_provenance(
    database_engine: Engine,
) -> None:
    debt = _technical_debt()
    with Session(database_engine) as session:
        persist_human_decision(session, _human_decision())
        persist_technical_debt(session, debt)
        session.commit()

    with Session(database_engine) as session:
        loaded = load_technical_debt(session, DEBT_ID)
        assert loaded == debt
        assert loaded is not None
        assert loaded.lifecycle_status is TechnicalDebtLifecycleStatus.REGISTERED
        assert loaded.created_at.tzinfo is not None
        persisted = session.get(TechnicalDebtModel, DEBT_ID)
        assert persisted is not None
        assert persisted.source_candidate_id == CANDIDATE_ID
        assert persisted.creation_human_decision_id == DECISION_ID


def test_persistence_helpers_leave_transaction_ownership_to_caller(
    database_engine: Engine,
) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        event.listen(session, "before_commit", mark_commit)
        persist_human_decision(session, _human_decision())
        persist_technical_debt(session, _technical_debt())
        assert committed is False


def test_duplicate_candidate_sequence_is_rejected_by_the_database(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        persist_human_decision(session, _human_decision())
        session.flush()
        session.add(
            HumanDecisionModel(
                human_decision_id=uuid4(),
                candidate_id=CANDIDATE_ID,
                sequence_number=1,
                decision_type=HumanDecisionType.REJECT.value,
                rationale="A second decision at the same sequence.",
                requested_information=None,
                actor_reference="poc:other-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_second_technical_debt_for_the_same_candidate_is_rejected(
    database_engine: Engine,
) -> None:
    second_decision_id = uuid4()
    with Session(database_engine) as session:
        persist_human_decision(session, _human_decision())
        persist_human_decision(
            session,
            _human_decision(
                human_decision_id=second_decision_id,
                sequence_number=2,
                decision_type=HumanDecisionType.REQUEST_INFO,
            ),
        )
        persist_technical_debt(session, _technical_debt())
        session.flush()
        session.add(
            TechnicalDebtModel(
                technical_debt_id=uuid4(),
                source_candidate_id=CANDIDATE_ID,
                creation_human_decision_id=second_decision_id,
                lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED.value,
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_second_technical_debt_for_the_same_creation_decision_is_rejected(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        persist_human_decision(session, _human_decision())
        persist_technical_debt(session, _technical_debt())
        session.flush()
        session.add(
            TechnicalDebtModel(
                technical_debt_id=uuid4(),
                source_candidate_id=SECOND_CANDIDATE_ID,
                creation_human_decision_id=DECISION_ID,
                lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED.value,
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_database_rejects_non_positive_sequence_number(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        session.add(
            HumanDecisionModel(
                human_decision_id=uuid4(),
                candidate_id=CANDIDATE_ID,
                sequence_number=0,
                decision_type=HumanDecisionType.VALIDATE.value,
                rationale="Sequence must start at one.",
                requested_information=None,
                actor_reference="poc:local-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_database_rejects_unsupported_technical_debt_lifecycle(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        persist_human_decision(session, _human_decision())
        session.add(
            TechnicalDebtModel(
                technical_debt_id=uuid4(),
                source_candidate_id=CANDIDATE_ID,
                creation_human_decision_id=DECISION_ID,
                lifecycle_status="CLOSED",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_database_rejects_unsupported_decision_type(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        session.add(
            HumanDecisionModel(
                human_decision_id=uuid4(),
                candidate_id=CANDIDATE_ID,
                sequence_number=1,
                decision_type="MERGE",
                rationale="Unsupported decision type.",
                requested_information=None,
                actor_reference="poc:local-reviewer",
                created_at=CREATED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()


def test_candidate_governance_lock_sql_uses_mssql_update_and_hold_hints() -> None:
    statement = candidate_governance_boundary_statement(CANDIDATE_ID)
    mssql_sql = str(statement.compile(dialect=mssql.dialect()))
    sqlite_sql = str(statement.compile(dialect=sqlite.dialect()))

    assert "UPDLOCK" in mssql_sql
    assert "HOLDLOCK" in mssql_sql
    assert "FOR UPDATE" not in mssql_sql
    assert "FROM candidates WITH (UPDLOCK, HOLDLOCK)" in mssql_sql
    assert "UPDLOCK" not in sqlite_sql
    assert "HOLDLOCK" not in sqlite_sql
    assert "FOR UPDATE" not in sqlite_sql


def test_human_decision_count_helper_starts_empty(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        assert session.scalar(select(func.count()).select_from(HumanDecisionModel)) == 0
        assert session.scalar(select(func.count()).select_from(TechnicalDebtModel)) == 0
