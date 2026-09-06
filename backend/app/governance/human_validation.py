from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.governance.contracts import (
    CandidateGovernanceSnapshot,
    CandidateNotFound,
    GovernancePersistenceConflict,
    HumanActorContext,
    HumanValidationCommand,
    StaleGovernanceRevision,
)
from app.governance.transitions import (
    derive_candidate_governance,
    next_governance_state,
    require_expected_governance_revision,
)
from app.infrastructure.database.human_decision_persistence import (
    load_human_decision_history,
    lock_candidate_for_governance,
    persist_human_decision,
)
from app.infrastructure.database.technical_debt_persistence import (
    persist_technical_debt,
)

_SEQUENCE_UNIQUENESS_MARKERS = (
    "uq_human_decisions_candidate_sequence",
    "human_decisions.candidate_id, human_decisions.sequence_number",
)
_SOURCE_CANDIDATE_UNIQUENESS_MARKERS = (
    "uq_technical_debts_source_candidate_id",
    "technical_debts.source_candidate_id",
)
_CREATION_DECISION_UNIQUENESS_MARKERS = (
    "uq_technical_debts_creation_human_decision_id",
    "technical_debts.creation_human_decision_id",
)


@dataclass(frozen=True)
class AppliedHumanValidation:
    """Durable result of one Human Validation command."""

    human_decision: HumanDecision
    technical_debt: TechnicalDebt | None
    governance: CandidateGovernanceSnapshot


def apply_human_validation(
    session: Session,
    command: HumanValidationCommand,
    actor_context: HumanActorContext,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> AppliedHumanValidation:
    """Apply one Human Validation command atomically.

    Actor identity comes from the server-owned HumanActorContext. The untrusted
    command cannot supply actor_reference, role, or authorization.

    The caller must supply a transaction-free Session. This service opens and
    owns the governance transaction; it does not join, commit, or roll back an
    existing caller transaction.
    """
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4

    if session.in_transaction():
        raise RuntimeError(
            "apply_human_validation requires a transaction-free Session; "
            "the service owns the governance transaction"
        )

    with session.begin():
        return _apply_human_validation(session, command, actor_context, now, next_id)


def _apply_human_validation(
    session: Session,
    command: HumanValidationCommand,
    actor_context: HumanActorContext,
    clock: Callable[[], datetime],
    new_id: Callable[[], UUID],
) -> AppliedHumanValidation:
    if lock_candidate_for_governance(session, command.candidate_id) is None:
        raise CandidateNotFound("Candidate does not exist")

    history = load_human_decision_history(session, command.candidate_id)
    current = derive_candidate_governance(history)
    require_expected_governance_revision(
        current.revision,
        command.expected_governance_revision,
    )
    next_governance_state(current.state, command.decision)

    created_at = clock()
    decision = HumanDecision(
        human_decision_id=new_id(),
        candidate_id=command.candidate_id,
        sequence_number=current.revision + 1,
        decision_type=command.decision,
        rationale=command.rationale,
        requested_information=command.requested_information,
        actor_reference=actor_context.actor_reference,
        created_at=created_at,
    )
    technical_debt = _technical_debt_for_decision(decision, new_id)

    try:
        persist_human_decision(session, decision)
        if technical_debt is not None:
            persist_technical_debt(session, technical_debt)
    except IntegrityError as error:
        raise map_governance_integrity_error(error) from error

    return AppliedHumanValidation(
        human_decision=decision,
        technical_debt=technical_debt,
        governance=derive_candidate_governance((*history, decision)),
    )


def _technical_debt_for_decision(
    decision: HumanDecision,
    new_id: Callable[[], UUID],
) -> TechnicalDebt | None:
    if decision.decision_type is not HumanDecisionType.VALIDATE:
        return None
    return TechnicalDebt(
        technical_debt_id=new_id(),
        source_candidate_id=decision.candidate_id,
        creation_human_decision_id=decision.human_decision_id,
        lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
        created_at=decision.created_at,
    )


def map_governance_integrity_error(error: IntegrityError) -> Exception:
    """Map a recognized uniqueness failure; leave unknown integrity errors intact."""
    message = str(error.orig) if error.orig is not None else str(error)
    normalized = message.lower()

    if _contains_any(normalized, _SEQUENCE_UNIQUENESS_MARKERS):
        return StaleGovernanceRevision(
            "expected_governance_revision does not match the current revision"
        )
    if _contains_any(normalized, _SOURCE_CANDIDATE_UNIQUENESS_MARKERS):
        return GovernancePersistenceConflict(
            "A TechnicalDebt already exists for this Candidate"
        )
    if _contains_any(normalized, _CREATION_DECISION_UNIQUENESS_MARKERS):
        return GovernancePersistenceConflict(
            "A TechnicalDebt already exists for this HumanDecision"
        )
    return error


def _contains_any(message: str, markers: tuple[str, ...]) -> bool:
    return any(marker.lower() in message for marker in markers)
