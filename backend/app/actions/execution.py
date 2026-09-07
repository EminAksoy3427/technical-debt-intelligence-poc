from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalDoesNotBelongToTechnicalDebt,
    ActionProposalNotFound,
    ExecuteActionProposalCommand,
    LogicalActionExecutionConflict,
    TechnicalDebtNotFound,
)
from app.actions.execution_policy import record_action_execution_policy_decision
from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutor,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.domain.action_executions import (
    ActionExecution,
    ActionExecutionErrorCategory,
    ActionExecutionStatus,
)
from app.domain.action_policy import ActionPolicyDecision, ActionPolicyOutcome
from app.infrastructure.database.action_approval_persistence import (
    load_action_approval_for_proposal,
    lock_technical_debt_for_action_approval,
)
from app.infrastructure.database.action_execution_persistence import (
    finalize_action_execution,
    load_action_execution_for_proposal,
    load_occupying_action_execution,
    persist_action_execution,
)
from app.infrastructure.database.action_proposal_persistence import load_action_proposal

_EXECUTION_UNIQUENESS_MARKERS = (
    "uq_action_executions_action_proposal_id",
    "action_executions.action_proposal_id",
    "uq_action_executions_live_logical_action",
    "action_executions.technical_debt_id, action_executions.action_type",
)


class ExecuteActionProposalDisposition(StrEnum):
    CREATED = "CREATED"
    EXISTING = "EXISTING"
    DENIED = "DENIED"


@dataclass(frozen=True)
class ExecuteActionProposalResult:
    disposition: ExecuteActionProposalDisposition
    execution: ActionExecution | None
    policy_decision: ActionPolicyDecision | None


@dataclass(frozen=True)
class _ClaimResult:
    public_result: ExecuteActionProposalResult
    executor_command: CreateGitHubIssueCommand | None


def execute_action_proposal(
    session: Session,
    command: ExecuteActionProposalCommand,
    allowed_target: ActionPreparationContext,
    execution_enabled: bool,
    executor: GitHubIssueExecutor | None,
    *,
    clock: Callable[[], datetime] | None = None,
    new_id: Callable[[], UUID] | None = None,
) -> ExecuteActionProposalResult:
    """Claim, execute, and finalize one immutable external action attempt."""
    if session.in_transaction():
        raise RuntimeError(
            "execute_action_proposal requires a transaction-free Session; "
            "the service owns all execution transactions"
        )
    now = clock or (lambda: datetime.now(UTC))
    next_id = new_id or uuid4

    with session.begin():
        claim = _claim_execution(
            session,
            command,
            allowed_target,
            execution_enabled,
            executor is not None,
            now,
            next_id,
        )

    if claim.executor_command is None:
        return claim.public_result

    if session.in_transaction():
        raise RuntimeError("GitHub issue executor cannot run inside a DB transaction")
    assert executor is not None
    try:
        external_result = executor.create_issue(claim.executor_command)
    except Exception:
        external_result = GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
        )

    execution = claim.public_result.execution
    assert execution is not None
    completed = _completed_execution(execution, external_result, now())
    with session.begin():
        finalize_action_execution(session, completed)
    return ExecuteActionProposalResult(
        disposition=ExecuteActionProposalDisposition.CREATED,
        execution=completed,
        policy_decision=claim.public_result.policy_decision,
    )


def _claim_execution(
    session: Session,
    command: ExecuteActionProposalCommand,
    allowed_target: ActionPreparationContext,
    execution_enabled: bool,
    executor_ready: bool,
    clock: Callable[[], datetime],
    new_id: Callable[[], UUID],
) -> _ClaimResult:
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

    existing = load_action_execution_for_proposal(
        session, command.action_proposal_id
    )
    if existing is not None:
        return _ClaimResult(
            public_result=ExecuteActionProposalResult(
                disposition=ExecuteActionProposalDisposition.EXISTING,
                execution=existing,
                policy_decision=None,
            ),
            executor_command=None,
        )

    occupying = load_occupying_action_execution(
        session,
        command.technical_debt_id,
        proposal.action_type,
    )
    if occupying is not None:
        raise LogicalActionExecutionConflict(
            "Another proposal occupies this logical external action"
        )

    approval = load_action_approval_for_proposal(session, proposal.action_proposal_id)
    decision = record_action_execution_policy_decision(
        session,
        proposal,
        approval,
        allowed_target,
        execution_enabled,
        executor_ready=executor_ready,
        clock=clock,
        new_id=new_id,
    )
    if decision.decision is ActionPolicyOutcome.DENY:
        return _ClaimResult(
            public_result=ExecuteActionProposalResult(
                disposition=ExecuteActionProposalDisposition.DENIED,
                execution=None,
                policy_decision=decision,
            ),
            executor_command=None,
        )

    execution = ActionExecution(
        action_execution_id=new_id(),
        action_proposal_id=proposal.action_proposal_id,
        technical_debt_id=proposal.technical_debt_id,
        action_type=proposal.action_type,
        creation_policy_decision_id=decision.action_policy_decision_id,
        status=ActionExecutionStatus.IN_PROGRESS,
        external_issue_id=None,
        external_issue_number=None,
        external_issue_url=None,
        safe_error_category=None,
        started_at=clock(),
        completed_at=None,
    )
    try:
        persist_action_execution(session, execution)
    except IntegrityError as error:
        mapped = map_action_execution_integrity_error(error)
        if mapped is error:
            raise
        raise mapped from error
    return _ClaimResult(
        public_result=ExecuteActionProposalResult(
            disposition=ExecuteActionProposalDisposition.CREATED,
            execution=execution,
            policy_decision=decision,
        ),
        executor_command=CreateGitHubIssueCommand(
            owner=proposal.target_repository_owner,
            repository=proposal.target_repository_name,
            title=proposal.payload.title,
            body=proposal.payload.body,
        ),
    )


def map_action_execution_integrity_error(error: IntegrityError) -> Exception:
    """Map only known durable execution uniqueness violations."""
    message = str(error.orig) if error.orig is not None else str(error)
    normalized = message.lower()
    if any(marker.lower() in normalized for marker in _EXECUTION_UNIQUENESS_MARKERS):
        return LogicalActionExecutionConflict(
            "Another execution already occupies this external action"
        )
    return error


def _completed_execution(
    execution: ActionExecution,
    result: GitHubIssueExecutorResult,
    completed_at: datetime,
) -> ActionExecution:
    if result.outcome is GitHubIssueExecutorOutcome.CREATED:
        status = ActionExecutionStatus.SUCCEEDED
        category = None
    elif result.outcome is GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN:
        status = ActionExecutionStatus.UNKNOWN
        category = ActionExecutionErrorCategory.TRANSPORT_UNKNOWN
    elif result.outcome is GitHubIssueExecutorOutcome.REJECTED:
        status = ActionExecutionStatus.FAILED
        category = ActionExecutionErrorCategory.EXTERNAL_REJECTED
    else:
        status = ActionExecutionStatus.FAILED
        category = ActionExecutionErrorCategory.NOT_SENT
    return ActionExecution(
        action_execution_id=execution.action_execution_id,
        action_proposal_id=execution.action_proposal_id,
        technical_debt_id=execution.technical_debt_id,
        action_type=execution.action_type,
        creation_policy_decision_id=execution.creation_policy_decision_id,
        status=status,
        external_issue_id=result.external_issue_id,
        external_issue_number=result.external_issue_number,
        external_issue_url=result.external_issue_url,
        safe_error_category=category,
        started_at=execution.started_at,
        completed_at=completed_at,
    )
