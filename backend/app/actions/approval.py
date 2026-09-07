from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionProposalAlreadyApproved,
    ActionProposalDoesNotBelongToTechnicalDebt,
    ActionProposalNotFound,
    ApproveActionProposalCommand,
    CompetingActionApprovalExists,
    StaleActionProposalFingerprint,
    TechnicalDebtNotFound,
)
from app.domain.action_approvals import ActionApproval
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_approval_persistence import (
    list_create_github_issue_approvals_for_technical_debt,
    lock_technical_debt_for_action_approval,
    persist_action_approval,
)
from app.infrastructure.database.action_proposal_persistence import load_action_proposal

_PROPOSAL_UNIQUENESS_MARKERS = (
    "uq_action_approvals_action_proposal_id",
    "action_approvals.action_proposal_id",
)


def approve_action_proposal(
    session: Session,
    command: ApproveActionProposalCommand,
    actor_context: HumanActorContext,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ActionApproval:
    """Persist one L4 approval for an exact ActionProposal fingerprint.

    Actor identity comes from the server-owned HumanActorContext. The untrusted
    command cannot supply actor_reference, repository, title, body, action type,
    or a policy decision.

    The caller must supply a transaction-free Session. This service opens and
    owns the approval transaction; it does not join, commit, or roll back an
    existing caller transaction.

    Approval is not policy ALLOW and does not execute an external action.
    """
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4

    if session.in_transaction():
        raise RuntimeError(
            "approve_action_proposal requires a transaction-free Session; "
            "the service owns the approval transaction"
        )

    with session.begin():
        return _approve_action_proposal(
            session,
            command,
            actor_context,
            now,
            next_id,
        )


def _approve_action_proposal(
    session: Session,
    command: ApproveActionProposalCommand,
    actor_context: HumanActorContext,
    clock: Callable[[], datetime],
    new_id: Callable[[], UUID],
) -> ActionApproval:
    if lock_technical_debt_for_action_approval(session, command.technical_debt_id) is (
        None
    ):
        raise TechnicalDebtNotFound("TechnicalDebt does not exist")

    proposal = load_action_proposal(session, command.action_proposal_id)
    if proposal is None:
        raise ActionProposalNotFound("ActionProposal does not exist")
    if proposal.technical_debt_id != command.technical_debt_id:
        raise ActionProposalDoesNotBelongToTechnicalDebt(
            "ActionProposal does not belong to TechnicalDebt"
        )
    if proposal.payload_fingerprint != command.expected_payload_fingerprint:
        raise StaleActionProposalFingerprint(
            "expected_payload_fingerprint does not match the persisted ActionProposal"
        )

    occupying = list_create_github_issue_approvals_for_technical_debt(
        session,
        command.technical_debt_id,
    )
    if occupying:
        if any(
            item.action_proposal_id == command.action_proposal_id for item in occupying
        ):
            raise ActionProposalAlreadyApproved("ActionProposal is already approved")
        raise CompetingActionApprovalExists(
            "A competing ActionProposal already holds approval for this logical action"
        )

    approval = ActionApproval(
        action_approval_id=new_id(),
        action_proposal_id=proposal.action_proposal_id,
        payload_fingerprint=proposal.payload_fingerprint,
        actor_reference=actor_context.actor_reference,
        created_at=clock(),
    )

    try:
        persist_action_approval(session, approval)
    except IntegrityError as error:
        raise map_action_approval_integrity_error(error) from error

    return approval


def map_action_approval_integrity_error(error: IntegrityError) -> Exception:
    """Map a recognized uniqueness failure; leave unknown integrity errors intact."""
    message = str(error.orig) if error.orig is not None else str(error)
    normalized = message.lower()
    if any(marker.lower() in normalized for marker in _PROPOSAL_UNIQUENESS_MARKERS):
        return ActionProposalAlreadyApproved("ActionProposal is already approved")
    return error
