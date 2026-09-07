from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.domain.action_approvals import ActionApproval
from app.domain.action_executions import ActionExecution
from app.domain.action_proposals import ActionProposal
from app.domain.action_verifications import ActionVerification
from app.domain.candidates import Candidate
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt
from app.infrastructure.database.action_approval_persistence import (
    list_action_approvals_for_technical_debt,
)
from app.infrastructure.database.action_execution_persistence import (
    list_action_executions_for_technical_debt,
)
from app.infrastructure.database.action_proposal_persistence import (
    list_action_proposals_for_technical_debt,
)
from app.infrastructure.database.action_verification_persistence import (
    list_action_verifications_for_technical_debt,
)
from app.infrastructure.database.candidate_persistence import load_candidate
from app.infrastructure.database.human_decision_persistence import load_human_decision
from app.infrastructure.database.technical_debt_persistence import (
    list_technical_debts,
    load_technical_debt,
)


class TechnicalDebtReadIntegrityError(ValueError):
    """Persisted TechnicalDebt facts cannot form the public read model."""


@dataclass(frozen=True)
class TechnicalDebtSummary:
    technical_debt: TechnicalDebt
    source_candidate: Candidate


@dataclass(frozen=True)
class TechnicalDebtDetail:
    technical_debt: TechnicalDebt
    source_candidate: Candidate
    creation_human_decision: HumanDecision
    action_proposals: tuple[ActionProposal, ...]
    action_approvals: tuple[ActionApproval, ...]
    action_executions: tuple[ActionExecution, ...]
    action_verifications: tuple[ActionVerification, ...]


def list_technical_debt_summaries(
    session: Session,
) -> tuple[TechnicalDebtSummary, ...]:
    """Load TechnicalDebt list items with source Candidate projections."""
    summaries = tuple(
        TechnicalDebtSummary(
            technical_debt=technical_debt,
            source_candidate=_require_source_candidate(
                session,
                technical_debt.source_candidate_id,
            ),
        )
        for technical_debt in list_technical_debts(session)
    )
    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                item.technical_debt.created_at,
                item.technical_debt.technical_debt_id.hex,
            ),
        )
    )


def load_technical_debt_detail(
    session: Session,
    technical_debt_id: UUID,
) -> TechnicalDebtDetail | None:
    """Load one TechnicalDebt with source Candidate and creating decision."""
    technical_debt = load_technical_debt(session, technical_debt_id)
    if technical_debt is None:
        return None

    source_candidate = _require_source_candidate(
        session,
        technical_debt.source_candidate_id,
    )
    creation_human_decision = load_human_decision(
        session,
        technical_debt.creation_human_decision_id,
    )
    if creation_human_decision is None:
        raise TechnicalDebtReadIntegrityError(
            "TechnicalDebt creation HumanDecision is unexpectedly missing"
        )
    if creation_human_decision.candidate_id != technical_debt.source_candidate_id:
        raise TechnicalDebtReadIntegrityError(
            "TechnicalDebt creation HumanDecision does not match the source Candidate"
        )
    if creation_human_decision.decision_type is not HumanDecisionType.VALIDATE:
        raise TechnicalDebtReadIntegrityError(
            "TechnicalDebt creation HumanDecision must be VALIDATE"
        )

    try:
        action_proposals = list_action_proposals_for_technical_debt(
            session,
            technical_debt.technical_debt_id,
        )
    except ValueError as error:
        raise TechnicalDebtReadIntegrityError(
            "Persisted ActionProposal data failed integrity validation"
        ) from error

    try:
        action_approvals = list_action_approvals_for_technical_debt(
            session,
            technical_debt.technical_debt_id,
        )
    except ValueError as error:
        raise TechnicalDebtReadIntegrityError(
            "Persisted ActionApproval data failed integrity validation"
        ) from error

    try:
        action_executions = list_action_executions_for_technical_debt(
            session,
            technical_debt.technical_debt_id,
        )
    except ValueError as error:
        raise TechnicalDebtReadIntegrityError(
            "Persisted ActionExecution data failed integrity validation"
        ) from error

    try:
        action_verifications = list_action_verifications_for_technical_debt(
            session,
            technical_debt.technical_debt_id,
        )
    except ValueError as error:
        raise TechnicalDebtReadIntegrityError(
            "Persisted ActionVerification data failed integrity validation"
        ) from error

    return TechnicalDebtDetail(
        technical_debt=technical_debt,
        source_candidate=source_candidate,
        creation_human_decision=creation_human_decision,
        action_proposals=action_proposals,
        action_approvals=action_approvals,
        action_executions=action_executions,
        action_verifications=action_verifications,
    )


def _require_source_candidate(session: Session, candidate_id: UUID) -> Candidate:
    candidate = load_candidate(session, candidate_id)
    if candidate is None:
        raise TechnicalDebtReadIntegrityError(
            "TechnicalDebt source Candidate is unexpectedly missing"
        )
    return candidate
