from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionExecutionDoesNotBelongToProposal,
    ActionExecutionNotFound,
    ActionExecutionNotVerifiable,
    ActionExecutionReconciliationUnresolved,
    ActionPreparationContext,
    ActionProposalDoesNotBelongToTechnicalDebt,
    ActionProposalNotFound,
    ActionVerificationUnavailable,
    TechnicalDebtNotFound,
    VerifyActionExecutionCommand,
)
from app.actions.github_issue_verifier import (
    GitHubIssueReadOutcome,
    GitHubIssueVerifier,
    ObservedGitHubIssue,
)
from app.domain.action_executions import ActionExecution, ActionExecutionStatus
from app.domain.action_proposals import (
    ActionProposal,
    canonical_action_payload_fingerprint,
)
from app.domain.action_verifications import (
    ActionVerification,
    ActionVerificationReasonCode,
    ActionVerificationResult,
)
from app.infrastructure.database.action_approval_persistence import (
    lock_technical_debt_for_action_approval,
)
from app.infrastructure.database.action_execution_persistence import (
    finalize_action_execution,
    load_action_execution,
    lock_action_execution,
    reconcile_unknown_execution_success,
)
from app.infrastructure.database.action_proposal_persistence import load_action_proposal
from app.infrastructure.database.action_verification_persistence import (
    persist_action_verification,
)


@dataclass(frozen=True)
class _VerificationPlan:
    execution: ActionExecution
    proposal: ActionProposal


@dataclass(frozen=True)
class _ExternalObservation:
    unavailable: bool
    issue: ObservedGitHubIssue | None
    conflict: ActionExecutionReconciliationUnresolved | None


def verify_action_execution(
    session: Session,
    command: VerifyActionExecutionCommand,
    allowed_target: ActionPreparationContext,
    verifier: GitHubIssueVerifier | None,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ActionVerification:
    """Read back one persisted execution without mutating GitHub or TechnicalDebt."""
    if session.in_transaction():
        raise RuntimeError(
            "verify_action_execution requires a transaction-free Session; "
            "the service owns all verification transactions"
        )
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4

    with session.begin():
        plan = _load_verification_plan(session, command, allowed_target)

    if verifier is None:
        raise ActionVerificationUnavailable("Action verification is not available")
    if session.in_transaction():
        raise RuntimeError("GitHub issue verifier cannot run inside a DB transaction")
    observation = _observe_external(plan, verifier)

    if observation.conflict is not None:
        raise observation.conflict

    with session.begin():
        return _persist_verification_outcome(
            session,
            plan,
            observation,
            now(),
            next_id(),
        )


def compare_observed_issue(
    proposal: ActionProposal,
    execution: ActionExecution,
    observed: ObservedGitHubIssue | None,
) -> tuple[ActionVerificationResult, ActionVerificationReasonCode | None]:
    """Compare persisted proposal authority to one observed GitHub issue."""
    if observed is None:
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.REFERENCE_MISMATCH,
        )
    if observed.is_pull_request:
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.PULL_REQUEST,
        )
    if not _reference_matches(proposal, execution, observed):
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.REFERENCE_MISMATCH,
        )
    if proposal.reconciliation_marker not in observed.body:
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.MARKER_MISSING,
        )
    if observed.title != proposal.payload.title:
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.TITLE_MISMATCH,
        )
    fingerprint = canonical_action_payload_fingerprint(
        action_type=proposal.action_type.value,
        target_repository_owner=proposal.target_repository_owner,
        target_repository_name=proposal.target_repository_name,
        title=observed.title,
        body=observed.body,
    )
    if fingerprint != proposal.payload_fingerprint:
        return (
            ActionVerificationResult.FAIL,
            ActionVerificationReasonCode.FINGERPRINT_MISMATCH,
        )
    return (ActionVerificationResult.PASS, None)


def _load_verification_plan(
    session: Session,
    command: VerifyActionExecutionCommand,
    allowed_target: ActionPreparationContext,
) -> _VerificationPlan:
    locked_debt = lock_technical_debt_for_action_approval(
        session,
        command.technical_debt_id,
    )
    if locked_debt is None:
        raise TechnicalDebtNotFound("TechnicalDebt does not exist")
    proposal = load_action_proposal(session, command.action_proposal_id)
    if proposal is None:
        raise ActionProposalNotFound("ActionProposal does not exist")
    if proposal.technical_debt_id != command.technical_debt_id:
        raise ActionProposalDoesNotBelongToTechnicalDebt(
            "ActionProposal does not belong to TechnicalDebt"
        )
    execution = load_action_execution(session, command.action_execution_id)
    if execution is None:
        raise ActionExecutionNotFound("ActionExecution does not exist")
    if (
        execution.action_proposal_id != command.action_proposal_id
        or execution.technical_debt_id != command.technical_debt_id
    ):
        raise ActionExecutionDoesNotBelongToProposal(
            "ActionExecution does not belong to ActionProposal"
        )
    if execution.status is ActionExecutionStatus.FAILED:
        raise ActionExecutionNotVerifiable("ActionExecution is not verifiable")
    if (
        proposal.target_repository_owner != allowed_target.target_repository_owner
        or proposal.target_repository_name != allowed_target.target_repository_name
    ):
        raise ActionVerificationUnavailable("Action verification is not available")
    return _VerificationPlan(execution=execution, proposal=proposal)


def _observe_external(
    plan: _VerificationPlan,
    verifier: GitHubIssueVerifier,
) -> _ExternalObservation:
    execution = plan.execution
    proposal = plan.proposal
    if execution.status is ActionExecutionStatus.SUCCEEDED:
        assert execution.external_issue_number is not None
        read = verifier.get_issue(
            proposal.target_repository_owner,
            proposal.target_repository_name,
            execution.external_issue_number,
        )
        if read.outcome is GitHubIssueReadOutcome.UNAVAILABLE:
            return _ExternalObservation(unavailable=True, issue=None, conflict=None)
        if read.outcome is GitHubIssueReadOutcome.NOT_FOUND:
            return _ExternalObservation(unavailable=False, issue=None, conflict=None)
        return _ExternalObservation(unavailable=False, issue=read.issue, conflict=None)

    search = verifier.find_issues_by_marker(
        proposal.target_repository_owner,
        proposal.target_repository_name,
        proposal.reconciliation_marker,
    )
    if search.outcome is GitHubIssueReadOutcome.UNAVAILABLE:
        return _ExternalObservation(unavailable=True, issue=None, conflict=None)

    candidates = tuple(
        issue
        for issue in search.issues
        if not issue.is_pull_request
        and proposal.reconciliation_marker in issue.body
    )
    if search.outcome is GitHubIssueReadOutcome.NOT_FOUND or len(candidates) == 0:
        return _unresolved("External issue could not be reconciled")
    if len(candidates) > 1:
        return _unresolved("External issue reconciliation is ambiguous")

    candidate = candidates[0]
    read = verifier.get_issue(
        proposal.target_repository_owner,
        proposal.target_repository_name,
        candidate.issue_number,
    )
    if read.outcome is GitHubIssueReadOutcome.UNAVAILABLE:
        if (
            proposal.reconciliation_marker in candidate.body
            and not candidate.is_pull_request
        ):
            return _ExternalObservation(
                unavailable=True, issue=candidate, conflict=None
            )
        return _ExternalObservation(unavailable=True, issue=None, conflict=None)
    if read.outcome is GitHubIssueReadOutcome.NOT_FOUND or read.issue is None:
        return _unresolved("External issue could not be reconciled")
    observed = read.issue
    if observed.is_pull_request or proposal.reconciliation_marker not in observed.body:
        return _unresolved("External issue could not be reconciled")
    return _ExternalObservation(unavailable=False, issue=observed, conflict=None)


def _unresolved(message: str) -> _ExternalObservation:
    return _ExternalObservation(
        unavailable=False,
        issue=None,
        conflict=ActionExecutionReconciliationUnresolved(message),
    )


def _persist_verification_outcome(
    session: Session,
    plan: _VerificationPlan,
    observation: _ExternalObservation,
    created_at: datetime,
    verification_id: UUID,
) -> ActionVerification:
    current = lock_action_execution(session, plan.execution.action_execution_id)
    if current is None:
        raise ActionExecutionNotFound("ActionExecution does not exist")
    if current.status is ActionExecutionStatus.FAILED:
        raise ActionExecutionNotVerifiable("ActionExecution is not verifiable")

    execution = _maybe_reconcile(
        session,
        current,
        plan.proposal,
        observation,
        created_at,
    )

    if observation.unavailable:
        verification = _unavailable_verification(
            verification_id, execution.action_execution_id, created_at
        )
        persist_action_verification(session, verification)
        return verification

    if execution.status is not ActionExecutionStatus.SUCCEEDED:
        raise ActionExecutionReconciliationUnresolved(
            "External issue could not be reconciled"
        )

    result, reason = compare_observed_issue(plan.proposal, execution, observation.issue)
    verification = ActionVerification(
        action_verification_id=verification_id,
        action_execution_id=execution.action_execution_id,
        result=result,
        observed_issue_number=(
            None if observation.issue is None else observation.issue.issue_number
        ),
        observed_issue_url=(
            None if observation.issue is None else observation.issue.html_url
        ),
        safe_reason_code=reason,
        created_at=created_at,
    )
    persist_action_verification(session, verification)
    return verification


def _maybe_reconcile(
    session: Session,
    current: ActionExecution,
    proposal: ActionProposal,
    observation: _ExternalObservation,
    completed_at: datetime,
) -> ActionExecution:
    if current.status is ActionExecutionStatus.SUCCEEDED:
        return current
    issue = observation.issue
    if (
        issue is None
        or issue.is_pull_request
        or proposal.reconciliation_marker not in issue.body
        or not _issue_has_recoverable_reference(issue)
    ):
        return current
    recovered = _succeeded_from_recovered_issue(current, issue, completed_at)
    if current.status is ActionExecutionStatus.UNKNOWN:
        reconcile_unknown_execution_success(session, recovered)
        return recovered
    if current.status is ActionExecutionStatus.IN_PROGRESS:
        finalize_action_execution(session, recovered)
        return recovered
    return current


def _succeeded_from_recovered_issue(
    current: ActionExecution,
    observed: ObservedGitHubIssue,
    completed_at: datetime,
) -> ActionExecution:
    return ActionExecution(
        action_execution_id=current.action_execution_id,
        action_proposal_id=current.action_proposal_id,
        technical_debt_id=current.technical_debt_id,
        action_type=current.action_type,
        creation_policy_decision_id=current.creation_policy_decision_id,
        status=ActionExecutionStatus.SUCCEEDED,
        external_issue_id=observed.issue_id,
        external_issue_number=observed.issue_number,
        external_issue_url=observed.html_url,
        safe_error_category=None,
        started_at=current.started_at,
        completed_at=(
            current.completed_at if current.completed_at is not None else completed_at
        ),
    )


def _unavailable_verification(
    verification_id: UUID,
    action_execution_id: UUID,
    created_at: datetime,
) -> ActionVerification:
    return ActionVerification(
        action_verification_id=verification_id,
        action_execution_id=action_execution_id,
        result=ActionVerificationResult.UNAVAILABLE,
        observed_issue_number=None,
        observed_issue_url=None,
        safe_reason_code=ActionVerificationReasonCode.TRANSPORT_UNAVAILABLE,
        created_at=created_at,
    )


def _issue_has_recoverable_reference(issue: ObservedGitHubIssue) -> bool:
    return (
        bool(issue.html_url.strip())
        and issue.issue_id > 0
        and issue.issue_number > 0
    )


def _reference_matches(
    proposal: ActionProposal,
    execution: ActionExecution,
    observed: ObservedGitHubIssue,
) -> bool:
    if execution.external_issue_number != observed.issue_number:
        return False
    if execution.external_issue_url != observed.html_url:
        return False
    parsed = urlparse(observed.html_url)
    parts = [item for item in parsed.path.split("/") if item]
    return (
        len(parts) >= 4
        and parts[0] == proposal.target_repository_owner
        and parts[1] == proposal.target_repository_name
        and parts[2] == "issues"
        and parts[3] == str(observed.issue_number)
    )
