from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.human_decision_models import HumanDecisionModel

_MSSQL_CANDIDATE_GOVERNANCE_LOCK = "WITH (UPDLOCK, HOLDLOCK)"


def candidate_governance_boundary_statement(
    candidate_id: UUID,
) -> Select[tuple[CandidateModel]]:
    """Select one Candidate with MSSQL UPDLOCK, HOLDLOCK on that dialect only."""
    return (
        select(CandidateModel)
        .where(CandidateModel.candidate_id == candidate_id)
        .with_hint(
            CandidateModel,
            _MSSQL_CANDIDATE_GOVERNANCE_LOCK,
            dialect_name="mssql",
        )
    )


def lock_candidate_for_governance(
    session: Session,
    candidate_id: UUID,
) -> CandidateModel | None:
    """Load the Candidate row that serializes Human Validation for that identity."""
    return session.scalar(candidate_governance_boundary_statement(candidate_id))


def persist_human_decision(session: Session, decision: HumanDecision) -> None:
    """Insert one append-only HumanDecision in the caller-owned transaction."""
    session.add(
        HumanDecisionModel(
            human_decision_id=decision.human_decision_id,
            candidate_id=decision.candidate_id,
            sequence_number=decision.sequence_number,
            decision_type=decision.decision_type.value,
            rationale=decision.rationale,
            requested_information=decision.requested_information,
            actor_reference=decision.actor_reference,
            created_at=decision.created_at,
        )
    )
    session.flush()


def load_human_decision(
    session: Session,
    human_decision_id: UUID,
) -> HumanDecision | None:
    persisted = session.get(HumanDecisionModel, human_decision_id)
    if persisted is None:
        return None
    return _human_decision_contract(persisted)


def load_human_decision_history(
    session: Session,
    candidate_id: UUID,
) -> tuple[HumanDecision, ...]:
    """Load one Candidate's HumanDecision history in sequence order."""
    persisted_decisions = session.scalars(
        select(HumanDecisionModel)
        .where(HumanDecisionModel.candidate_id == candidate_id)
        .order_by(HumanDecisionModel.sequence_number.asc())
    )
    return tuple(
        _human_decision_contract(persisted) for persisted in persisted_decisions
    )


def _human_decision_contract(persisted: HumanDecisionModel) -> HumanDecision:
    return HumanDecision(
        human_decision_id=persisted.human_decision_id,
        candidate_id=persisted.candidate_id,
        sequence_number=persisted.sequence_number,
        decision_type=HumanDecisionType(persisted.decision_type),
        rationale=persisted.rationale,
        requested_information=persisted.requested_information,
        actor_reference=persisted.actor_reference,
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
