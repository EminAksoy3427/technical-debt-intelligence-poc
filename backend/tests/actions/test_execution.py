from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.actions.approval import approve_action_proposal
from app.actions.contracts import (
    ActionPreparationContext,
    ApproveActionProposalCommand,
    CompetingActionApprovalExists,
    ExecuteActionProposalCommand,
    LogicalActionExecutionConflict,
)
from app.actions.execution import (
    ExecuteActionProposalDisposition,
    execute_action_proposal,
    map_action_execution_integrity_error,
)
from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutor,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.domain.action_approvals import ActionApproval
from app.domain.action_executions import ActionExecutionStatus
from app.domain.action_policy import ActionPolicyOutcome, ActionPolicyReasonCode
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_approval_persistence import (
    persist_action_approval,
)
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.base import Base
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel

NOW = datetime(2026, 9, 7, 20, 0, tzinfo=UTC)
DEBT_ID = UUID("10000000-0000-0000-0000-000000000001")
PROPOSAL_A = UUID("20000000-0000-0000-0000-000000000001")
PROPOSAL_B = UUID("20000000-0000-0000-0000-000000000002")
TARGET = ActionPreparationContext("demo-owner", "demo-repository")


class FakeExecutor:
    def __init__(
        self,
        session: Session,
        result: GitHubIssueExecutorResult,
    ) -> None:
        self.session = session
        self.result = result
        self.commands: list[CreateGitHubIssueCommand] = []

    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        assert not self.session.in_transaction()
        self.commands.append(command)
        return self.result


class ProcessCrashExecutor:
    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        raise KeyboardInterrupt


@pytest.fixture
def engine():
    database = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(database)
    yield database
    database.dispose()


def _proposal(proposal_id: UUID) -> ActionProposal:
    marker = action_proposal_reconciliation_marker(proposal_id)
    payload = GitHubIssuePayload(
        title=f"Exact title {proposal_id}",
        body=f"Exact body\n\n{marker}",
    )
    fingerprint = canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner=TARGET.target_repository_owner,
        target_repository_name=TARGET.target_repository_name,
        title=payload.title,
        body=payload.body,
    )
    return ActionProposal(
        action_proposal_id=proposal_id,
        technical_debt_id=DEBT_ID,
        action_type=ActionType.CREATE_GITHUB_ISSUE,
        target_repository_owner=TARGET.target_repository_owner,
        target_repository_name=TARGET.target_repository_name,
        payload=payload,
        payload_fingerprint=fingerprint,
        reconciliation_marker=marker,
        prepared_by="poc:reviewer",
        created_at=NOW,
    )


def _seed(session: Session, *proposal_ids: UUID, approve: bool = True) -> None:
    session.add(
        TechnicalDebtModel(
            technical_debt_id=DEBT_ID,
            source_candidate_id=UUID("30000000-0000-0000-0000-000000000001"),
            creation_human_decision_id=UUID(
                "40000000-0000-0000-0000-000000000001"
            ),
            lifecycle_status="REGISTERED",
            created_at=NOW,
        )
    )
    for index, proposal_id in enumerate(proposal_ids, start=1):
        proposal = _proposal(proposal_id)
        persist_action_proposal(session, proposal)
        if approve:
            persist_action_approval(
                session,
                ActionApproval(
                    action_approval_id=UUID(
                        f"50000000-0000-0000-0000-{index:012d}"
                    ),
                    action_proposal_id=proposal_id,
                    payload_fingerprint=proposal.payload_fingerprint,
                    actor_reference="poc:reviewer",
                    created_at=NOW,
                ),
            )
    session.commit()


def _execute(
    session: Session,
    proposal_id: UUID,
    executor: GitHubIssueExecutor | None,
):
    return execute_action_proposal(
        session,
        ExecuteActionProposalCommand(DEBT_ID, proposal_id),
        TARGET,
        True,
        executor,
        clock=lambda: NOW + timedelta(minutes=1),
    )


def test_created_executes_exact_persisted_payload_outside_transaction_and_deduplicates(
    engine,
) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A)
        executor = FakeExecutor(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.CREATED,
                external_issue_id=123,
                external_issue_number=7,
                external_issue_url="https://github.example/issues/7",
            ),
        )

        created = _execute(session, PROPOSAL_A, executor)
        duplicate = _execute(session, PROPOSAL_A, executor)

        assert created.execution is not None
        assert created.execution.status is ActionExecutionStatus.SUCCEEDED
        assert duplicate.disposition is ExecuteActionProposalDisposition.EXISTING
        assert duplicate.execution == created.execution
        assert executor.commands == [
            CreateGitHubIssueCommand(
                owner="demo-owner",
                repository="demo-repository",
                title=_proposal(PROPOSAL_A).payload.title,
                body=_proposal(PROPOSAL_A).payload.body,
            )
        ]
        policy = session.get(
            ActionPolicyDecisionModel,
            created.execution.creation_policy_decision_id,
        )
        assert policy is not None
        assert policy.decision == ActionPolicyOutcome.ALLOW.value


@pytest.mark.parametrize(
    ("outcome", "expected_status"),
    [
        (GitHubIssueExecutorOutcome.REJECTED, ActionExecutionStatus.FAILED),
        (GitHubIssueExecutorOutcome.NOT_SENT, ActionExecutionStatus.FAILED),
        (GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN, ActionExecutionStatus.UNKNOWN),
    ],
)
def test_external_outcomes_are_mapped_without_retry(
    engine,
    outcome: GitHubIssueExecutorOutcome,
    expected_status: ActionExecutionStatus,
) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A)
        executor = FakeExecutor(session, GitHubIssueExecutorResult(outcome=outcome))

        first = _execute(session, PROPOSAL_A, executor)
        second = _execute(session, PROPOSAL_A, executor)

        assert first.execution is not None
        assert first.execution.status is expected_status
        assert second.execution == first.execution
        assert len(executor.commands) == 1


def test_missing_executor_persists_deny_and_creates_no_execution(engine) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A)

        result = _execute(session, PROPOSAL_A, None)

        assert result.disposition is ExecuteActionProposalDisposition.DENIED
        assert result.policy_decision is not None
        assert (
            result.policy_decision.reason_code
            is ActionPolicyReasonCode.EXECUTION_DISABLED
        )
        execution_count = session.scalar(
            select(func.count()).select_from(ActionExecutionModel)
        )
        assert execution_count == 0
        assert (
            session.scalar(select(func.count()).select_from(ActionPolicyDecisionModel))
            == 1
        )


def test_proposal_uniqueness_maps_to_logical_execution_conflict() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "Violation of UNIQUE KEY constraint "
            "'uq_action_executions_action_proposal_id'"
        ),
    )

    mapped = map_action_execution_integrity_error(error)

    assert isinstance(mapped, LogicalActionExecutionConflict)


def test_logical_action_uniqueness_maps_to_logical_execution_conflict() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "Cannot insert duplicate key row with unique index "
            "'uq_action_executions_live_logical_action'"
        ),
    )

    mapped = map_action_execution_integrity_error(error)

    assert isinstance(mapped, LogicalActionExecutionConflict)


def test_unknown_integrity_error_remains_original_integrity_error() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception("FOREIGN KEY constraint failed"),
    )

    mapped = map_action_execution_integrity_error(error)

    assert mapped is error
    assert isinstance(mapped, IntegrityError)


def test_different_proposal_conflicts_while_unknown_occupies(engine) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A, PROPOSAL_B)
        executor = FakeExecutor(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        _execute(session, PROPOSAL_A, executor)

        with pytest.raises(LogicalActionExecutionConflict):
            _execute(session, PROPOSAL_B, executor)
        assert len(executor.commands) == 1


def test_definite_failed_execution_releases_approval_slot(engine) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A, PROPOSAL_B, approve=False)
        proposal_a = _proposal(PROPOSAL_A)
        proposal_b = _proposal(PROPOSAL_B)
        actor = HumanActorContext(actor_reference="poc:reviewer")
        approve_action_proposal(
            session,
            ApproveActionProposalCommand(
                DEBT_ID, PROPOSAL_A, proposal_a.payload_fingerprint
            ),
            actor,
            clock=lambda: NOW,
        )
        executor = FakeExecutor(
            session,
            GitHubIssueExecutorResult(outcome=GitHubIssueExecutorOutcome.REJECTED),
        )
        failed = _execute(session, PROPOSAL_A, executor)
        assert failed.execution is not None
        assert failed.execution.status is ActionExecutionStatus.FAILED

        approval_b = approve_action_proposal(
            session,
            ApproveActionProposalCommand(
                DEBT_ID, PROPOSAL_B, proposal_b.payload_fingerprint
            ),
            actor,
            clock=lambda: NOW + timedelta(minutes=2),
        )
        assert approval_b.action_proposal_id == PROPOSAL_B


@pytest.mark.parametrize(
    "outcome",
    (
        GitHubIssueExecutorOutcome.CREATED,
        GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN,
    ),
)
def test_succeeded_or_unknown_execution_keeps_approval_slot(
    engine,
    outcome: GitHubIssueExecutorOutcome,
) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A, PROPOSAL_B, approve=False)
        proposal_a = _proposal(PROPOSAL_A)
        proposal_b = _proposal(PROPOSAL_B)
        actor = HumanActorContext(actor_reference="poc:reviewer")
        approve_action_proposal(
            session,
            ApproveActionProposalCommand(
                DEBT_ID, PROPOSAL_A, proposal_a.payload_fingerprint
            ),
            actor,
        )
        result = (
            GitHubIssueExecutorResult(
                outcome=outcome,
                external_issue_id=1,
                external_issue_number=1,
                external_issue_url="https://github.example/issues/1",
            )
            if outcome is GitHubIssueExecutorOutcome.CREATED
            else GitHubIssueExecutorResult(outcome=outcome)
        )
        _execute(session, PROPOSAL_A, FakeExecutor(session, result))

        with pytest.raises(CompetingActionApprovalExists):
            approve_action_proposal(
                session,
                ApproveActionProposalCommand(
                    DEBT_ID, PROPOSAL_B, proposal_b.payload_fingerprint
                ),
                actor,
            )


def test_crash_after_claim_leaves_in_progress_and_never_reposts(engine) -> None:
    with Session(engine) as session:
        _seed(session, PROPOSAL_A)

        with pytest.raises(KeyboardInterrupt):
            _execute(session, PROPOSAL_A, ProcessCrashExecutor())
        existing = _execute(
            session,
            PROPOSAL_A,
            FakeExecutor(
                session,
                GitHubIssueExecutorResult(outcome=GitHubIssueExecutorOutcome.REJECTED),
            ),
        )

        assert existing.disposition is ExecuteActionProposalDisposition.EXISTING
        assert existing.execution is not None
        assert existing.execution.status is ActionExecutionStatus.IN_PROGRESS
