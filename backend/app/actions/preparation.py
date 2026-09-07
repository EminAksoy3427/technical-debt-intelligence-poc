from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.composition import (
    compose_github_issue_body,
    compose_github_issue_title,
)
from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalPersistenceConflict,
    ActionProposalSourceContextMissing,
    PrepareActionProposalCommand,
    TechnicalDebtNotFound,
    TechnicalDebtNotRegistered,
)
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.technical_debts import TechnicalDebtLifecycleStatus
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.candidate_persistence import load_candidate
from app.infrastructure.database.technical_debt_persistence import load_technical_debt

_MARKER_UNIQUENESS_MARKERS = (
    "uq_action_proposals_reconciliation_marker",
    "action_proposals.reconciliation_marker",
)


def prepare_action_proposal(
    session: Session,
    command: PrepareActionProposalCommand,
    actor_context: HumanActorContext,
    preparation_context: ActionPreparationContext,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ActionProposal:
    """Persist one immutable CREATE_GITHUB_ISSUE preview. No external side effect.

    Actor identity and target repository come from server-owned context. The
    untrusted command cannot supply repository, title, body, fingerprint,
    marker, actor, or action type.

    The caller must supply a transaction-free Session. This service opens and
    owns the preparation transaction; it does not join, commit, or roll back an
    existing caller transaction.
    """
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4

    if session.in_transaction():
        raise RuntimeError(
            "prepare_action_proposal requires a transaction-free Session; "
            "the service owns the preparation transaction"
        )

    with session.begin():
        return _prepare_action_proposal(
            session,
            command,
            actor_context,
            preparation_context,
            now,
            next_id,
        )


def _prepare_action_proposal(
    session: Session,
    command: PrepareActionProposalCommand,
    actor_context: HumanActorContext,
    preparation_context: ActionPreparationContext,
    clock: Callable[[], datetime],
    new_id: Callable[[], UUID],
) -> ActionProposal:
    technical_debt = load_technical_debt(session, command.technical_debt_id)
    if technical_debt is None:
        raise TechnicalDebtNotFound("TechnicalDebt does not exist")
    if technical_debt.lifecycle_status is not TechnicalDebtLifecycleStatus.REGISTERED:
        raise TechnicalDebtNotRegistered("TechnicalDebt is not REGISTERED")

    candidate = load_candidate(session, technical_debt.source_candidate_id)
    if candidate is None:
        raise ActionProposalSourceContextMissing(
            "TechnicalDebt source Candidate is unexpectedly missing"
        )

    action_proposal_id = new_id()
    reconciliation_marker = action_proposal_reconciliation_marker(action_proposal_id)
    title = compose_github_issue_title(candidate)
    body = compose_github_issue_body(
        technical_debt=technical_debt,
        candidate=candidate,
        action_proposal_id=action_proposal_id,
    )
    payload = GitHubIssuePayload(title=title, body=body)
    payload_fingerprint = canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner=preparation_context.target_repository_owner,
        target_repository_name=preparation_context.target_repository_name,
        title=payload.title,
        body=payload.body,
    )
    proposal = ActionProposal(
        action_proposal_id=action_proposal_id,
        technical_debt_id=technical_debt.technical_debt_id,
        action_type=ActionType.CREATE_GITHUB_ISSUE,
        target_repository_owner=preparation_context.target_repository_owner,
        target_repository_name=preparation_context.target_repository_name,
        payload=payload,
        payload_fingerprint=payload_fingerprint,
        reconciliation_marker=reconciliation_marker,
        prepared_by=actor_context.actor_reference,
        created_at=clock(),
    )

    try:
        persist_action_proposal(session, proposal)
    except IntegrityError as error:
        raise map_action_proposal_integrity_error(error) from error

    return proposal


def map_action_proposal_integrity_error(error: IntegrityError) -> Exception:
    """Map a recognized uniqueness failure; leave unknown integrity errors intact."""
    message = str(error.orig) if error.orig is not None else str(error)
    normalized = message.lower()
    if any(marker.lower() in normalized for marker in _MARKER_UNIQUENESS_MARKERS):
        return ActionProposalPersistenceConflict(
            "An ActionProposal already exists for this reconciliation marker"
        )
    return error
