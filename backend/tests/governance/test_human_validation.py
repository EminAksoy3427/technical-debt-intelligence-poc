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

from app.domain.human_decisions import HumanDecisionType
from app.domain.technical_debts import TechnicalDebtLifecycleStatus
from app.governance.contracts import (
    CandidateGovernanceState,
    CandidateNotFound,
    GovernancePersistenceConflict,
    HumanActorContext,
    HumanValidationCommand,
    InvalidGovernanceTransition,
    StaleGovernanceRevision,
)
from app.governance.human_validation import (
    AppliedHumanValidation,
    apply_human_validation,
    map_governance_integrity_error,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.human_decision_persistence import (
    load_human_decision_history,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_persistence import (
    load_technical_debt_for_candidate,
)

CREATED_AT = datetime(2026, 9, 6, 17, 30, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
ACTOR = HumanActorContext(actor_reference="poc:local-reviewer")


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

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
        asset = EnterpriseAssetModel(
            asset_key="repo-borealis-renderer",
            asset_type="REPOSITORY",
            name="Borealis Renderer Repository",
            criticality="MEDIUM",
            lifecycle_status="ACTIVE",
        )
        signal = SignalModel(
            signal_id=uuid4(),
            source_system="human-validation-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="human-validation-test",
                    source_reference="source-721",
                    captured_at=CREATED_AT,
                )
            ],
        )
        session.add(
            CandidateModel(
                candidate_id=CANDIDATE_ID,
                canonical_asset=asset,
                hypothesis="Potential missing request timeout",
                correlation_rationale=(
                    "Persisted Signals share an asset and problem family."
                ),
                signal_memberships=[CandidateSignalModel(signal=signal)],
            )
        )
        session.commit()

    yield engine
    engine.dispose()


def _command(
    *,
    decision: HumanDecisionType = HumanDecisionType.VALIDATE,
    expected_governance_revision: int = 0,
    rationale: str | None = "The Candidate is a validated structural issue.",
    requested_information: str | None = None,
    candidate_id: UUID = CANDIDATE_ID,
) -> HumanValidationCommand:
    return HumanValidationCommand(
        candidate_id=candidate_id,
        decision=decision,
        expected_governance_revision=expected_governance_revision,
        rationale=rationale,
        requested_information=requested_information,
    )


def _apply(
    engine: Engine,
    command: HumanValidationCommand,
    actor: HumanActorContext = ACTOR,
) -> AppliedHumanValidation:
    with Session(engine) as session:
        return apply_human_validation(
            session,
            command,
            actor,
            clock=lambda: CREATED_AT,
        )


def _counts(engine: Engine, candidate_id: UUID = CANDIDATE_ID) -> tuple[int, int]:
    with Session(engine) as session:
        decisions = session.scalar(
            select(func.count())
            .select_from(HumanDecisionModel)
            .where(HumanDecisionModel.candidate_id == candidate_id)
        )
        debts = session.scalar(
            select(func.count())
            .select_from(TechnicalDebtModel)
            .where(TechnicalDebtModel.source_candidate_id == candidate_id)
        )
        return int(decisions or 0), int(debts or 0)


def test_validate_creates_decision_one_and_registered_technical_debt(
    database_engine: Engine,
) -> None:
    result = _apply(database_engine, _command())

    assert result.human_decision.sequence_number == 1
    assert result.human_decision.decision_type is HumanDecisionType.VALIDATE
    assert result.human_decision.actor_reference == ACTOR.actor_reference
    assert result.human_decision.created_at == CREATED_AT
    assert result.technical_debt is not None
    assert result.technical_debt.source_candidate_id == CANDIDATE_ID
    assert (
        result.technical_debt.creation_human_decision_id
        == result.human_decision.human_decision_id
    )
    assert (
        result.technical_debt.lifecycle_status
        is TechnicalDebtLifecycleStatus.REGISTERED
    )
    assert result.governance.state is CandidateGovernanceState.VALIDATED
    assert result.governance.revision == 1
    assert _counts(database_engine) == (1, 1)

    with Session(database_engine) as session:
        loaded_debt = load_technical_debt_for_candidate(session, CANDIDATE_ID)
        history = load_human_decision_history(session, CANDIDATE_ID)
        assert loaded_debt == result.technical_debt
        assert history == (result.human_decision,)


def test_reject_persists_decision_and_creates_no_technical_debt(
    database_engine: Engine,
) -> None:
    result = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REJECT,
            rationale="The findings do not form a structural issue.",
        ),
    )

    assert result.human_decision.decision_type is HumanDecisionType.REJECT
    assert result.technical_debt is None
    assert result.governance.state is CandidateGovernanceState.REJECTED
    assert _counts(database_engine) == (1, 0)


def test_request_info_persists_decision_and_creates_no_technical_debt(
    database_engine: Engine,
) -> None:
    result = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information="Who owns the renderer service?",
        ),
    )

    assert result.human_decision.decision_type is HumanDecisionType.REQUEST_INFO
    assert result.technical_debt is None
    assert result.governance.state is CandidateGovernanceState.INFORMATION_REQUESTED
    assert _counts(database_engine) == (1, 0)


def test_request_info_then_validate_creates_two_decisions_and_one_debt(
    database_engine: Engine,
) -> None:
    first = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information="Need the owning team.",
        ),
    )
    second = _apply(
        database_engine,
        _command(expected_governance_revision=1),
    )

    assert first.human_decision.sequence_number == 1
    assert second.human_decision.sequence_number == 2
    assert second.governance.state is CandidateGovernanceState.VALIDATED
    assert second.technical_debt is not None
    assert _counts(database_engine) == (2, 1)


def test_request_info_then_reject_is_rejected_without_technical_debt(
    database_engine: Engine,
) -> None:
    _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information="Need the owning team.",
        ),
    )
    result = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REJECT,
            expected_governance_revision=1,
            rationale="Not a structural issue after the extra context.",
        ),
    )

    assert result.governance.state is CandidateGovernanceState.REJECTED
    assert result.technical_debt is None
    assert _counts(database_engine) == (2, 0)


def test_repeated_request_info_increments_sequence_against_latest_revision(
    database_engine: Engine,
) -> None:
    first = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information="Need the owning team.",
        ),
    )
    second = _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            expected_governance_revision=1,
            rationale=None,
            requested_information="Need the blast radius as well.",
        ),
    )

    assert first.human_decision.sequence_number == 1
    assert second.human_decision.sequence_number == 2
    assert second.governance.state is CandidateGovernanceState.INFORMATION_REQUESTED
    assert second.governance.revision == 2
    assert _counts(database_engine) == (2, 0)


def test_missing_candidate_is_typed_and_writes_nothing(
    database_engine: Engine,
) -> None:
    unknown_id = uuid4()
    with pytest.raises(CandidateNotFound, match="Candidate does not exist"):
        _apply(database_engine, _command(candidate_id=unknown_id))

    assert _counts(database_engine, unknown_id) == (0, 0)
    assert _counts(database_engine) == (0, 0)


def test_stale_revision_is_typed_and_writes_nothing(database_engine: Engine) -> None:
    _apply(
        database_engine,
        _command(
            decision=HumanDecisionType.REQUEST_INFO,
            rationale=None,
            requested_information="Need the owning team.",
        ),
    )

    with pytest.raises(StaleGovernanceRevision, match="does not match"):
        _apply(database_engine, _command())

    assert _counts(database_engine) == (1, 0)


def test_terminal_state_rejects_follow_on_decision_without_writes(
    database_engine: Engine,
) -> None:
    _apply(database_engine, _command())

    with pytest.raises(InvalidGovernanceTransition, match="not a legal transition"):
        _apply(
            database_engine,
            _command(
                decision=HumanDecisionType.REJECT,
                expected_governance_revision=1,
                rationale="Too late to reject.",
            ),
        )

    assert _counts(database_engine) == (1, 1)


def test_second_validate_from_the_same_revision_is_a_conflict(
    database_engine: Engine,
) -> None:
    first = _apply(database_engine, _command())

    with pytest.raises(StaleGovernanceRevision):
        _apply(database_engine, _command())

    assert first.technical_debt is not None
    assert _counts(database_engine) == (1, 1)


def test_actor_reference_comes_from_server_context_not_the_command(
    database_engine: Engine,
) -> None:
    actor = HumanActorContext(actor_reference="poc:governance-reviewer")
    result = _apply(database_engine, _command(), actor)

    assert result.human_decision.actor_reference == "poc:governance-reviewer"
    assert not hasattr(result.human_decision, "role")


def test_active_session_transaction_is_rejected_before_writes(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        session.get(CandidateModel, CANDIDATE_ID)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            apply_human_validation(
                session,
                _command(),
                ACTOR,
                clock=lambda: CREATED_AT,
            )
        assert session.in_transaction()

    assert _counts(database_engine) == (0, 0)


def test_validate_rolls_back_when_technical_debt_persistence_fails(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_technical_debt(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("forced TechnicalDebt persistence failure")

    monkeypatch.setattr(
        "app.governance.human_validation.persist_technical_debt",
        fail_technical_debt,
    )

    with Session(database_engine) as session:
        with pytest.raises(RuntimeError, match="forced TechnicalDebt"):
            apply_human_validation(
                session,
                _command(),
                ACTOR,
                clock=lambda: CREATED_AT,
            )

    assert _counts(database_engine) == (0, 0)


def test_sequence_uniqueness_maps_to_stale_revision() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "UNIQUE constraint failed: human_decisions.candidate_id, "
            "human_decisions.sequence_number"
        ),
    )

    mapped = map_governance_integrity_error(error)

    assert isinstance(mapped, StaleGovernanceRevision)


def test_technical_debt_uniqueness_maps_to_persistence_conflict() -> None:
    source_error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "Violation of UNIQUE KEY constraint "
            "'uq_technical_debts_source_candidate_id'"
        ),
    )
    creation_error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "Violation of UNIQUE KEY constraint "
            "'uq_technical_debts_creation_human_decision_id'"
        ),
    )

    assert isinstance(
        map_governance_integrity_error(source_error),
        GovernancePersistenceConflict,
    )
    assert isinstance(
        map_governance_integrity_error(creation_error),
        GovernancePersistenceConflict,
    )


def test_unknown_integrity_error_is_not_converted_to_governance_semantics() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception("FOREIGN KEY constraint failed"),
    )

    assert map_governance_integrity_error(error) is error
