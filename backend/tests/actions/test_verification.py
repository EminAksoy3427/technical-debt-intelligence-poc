from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.actions.contracts import (
    ActionExecutionNotVerifiable,
    ActionExecutionReconciliationUnresolved,
    ActionPreparationContext,
    ActionVerificationUnavailable,
    ExecuteActionProposalCommand,
    VerifyActionExecutionCommand,
)
from app.actions.execution import execute_action_proposal
from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.actions.github_issue_verifier import (
    GitHubIssueReadOutcome,
    GitHubIssueReadResult,
    GitHubIssueSearchResult,
    ObservedGitHubIssue,
)
from app.actions.verification import verify_action_execution
from app.domain.action_approvals import ActionApproval
from app.domain.action_executions import ActionExecutionStatus
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.action_verifications import (
    ActionVerificationReasonCode,
    ActionVerificationResult,
)
from app.infrastructure.database.action_approval_persistence import (
    persist_action_approval,
)
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_execution_persistence import (
    reconcile_unknown_execution_success,
)
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.action_verification_models import (
    ActionVerificationModel,
)
from app.infrastructure.database.base import Base
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel

NOW = datetime(2026, 9, 7, 21, 0, tzinfo=UTC)
DEBT_ID = UUID("10000000-0000-0000-0000-000000000001")
PROPOSAL_A = UUID("20000000-0000-0000-0000-000000000001")
TARGET = ActionPreparationContext("demo-owner", "demo-repository")
ISSUE_URL = "https://github.com/demo-owner/demo-repository/issues/7"


class ProcessCrashExecutor:
    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        raise KeyboardInterrupt


class FakeExecutor:
    def __init__(self, result: GitHubIssueExecutorResult) -> None:
        self.result = result
        self.commands: list[CreateGitHubIssueCommand] = []

    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        self.commands.append(command)
        return self.result


class FakeVerifier:
    def __init__(
        self,
        session: Session,
        *,
        issue: ObservedGitHubIssue | None = None,
        get_outcome: GitHubIssueReadOutcome = GitHubIssueReadOutcome.FOUND,
        search_issues: tuple[ObservedGitHubIssue, ...] = (),
        search_outcome: GitHubIssueReadOutcome = GitHubIssueReadOutcome.FOUND,
    ) -> None:
        self.session = session
        self.issue = issue
        self.get_outcome = get_outcome
        self.search_issues = search_issues
        self.search_outcome = search_outcome
        self.get_calls: list[tuple[str, str, int]] = []
        self.search_calls: list[tuple[str, str, str]] = []

    def get_issue(
        self,
        owner: str,
        repository: str,
        issue_number: int,
    ) -> GitHubIssueReadResult:
        assert not self.session.in_transaction()
        self.get_calls.append((owner, repository, issue_number))
        if self.get_outcome is GitHubIssueReadOutcome.FOUND:
            assert self.issue is not None
            return GitHubIssueReadResult(
                outcome=GitHubIssueReadOutcome.FOUND,
                issue=self.issue,
            )
        return GitHubIssueReadResult(outcome=self.get_outcome)

    def find_issues_by_marker(
        self,
        owner: str,
        repository: str,
        marker: str,
    ) -> GitHubIssueSearchResult:
        assert not self.session.in_transaction()
        self.search_calls.append((owner, repository, marker))
        if self.search_outcome is GitHubIssueReadOutcome.FOUND:
            return GitHubIssueSearchResult(
                outcome=GitHubIssueReadOutcome.FOUND,
                issues=self.search_issues,
            )
        return GitHubIssueSearchResult(outcome=self.search_outcome)


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


def _proposal(proposal_id: UUID = PROPOSAL_A) -> ActionProposal:
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


def _matching_issue(
    proposal: ActionProposal,
    *,
    number: int = 7,
    title: str | None = None,
    body: str | None = None,
    html_url: str | None = None,
    is_pull_request: bool = False,
) -> ObservedGitHubIssue:
    return ObservedGitHubIssue(
        issue_id=9000 + number,
        issue_number=number,
        html_url=html_url or ISSUE_URL,
        title=proposal.payload.title if title is None else title,
        body=proposal.payload.body if body is None else body,
        is_pull_request=is_pull_request,
    )


def _seed(session: Session, proposal_id: UUID = PROPOSAL_A) -> ActionProposal:
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
    proposal = _proposal(proposal_id)
    persist_action_proposal(session, proposal)
    persist_action_approval(
        session,
        ActionApproval(
            action_approval_id=UUID("50000000-0000-0000-0000-000000000001"),
            action_proposal_id=proposal_id,
            payload_fingerprint=proposal.payload_fingerprint,
            actor_reference="poc:reviewer",
            created_at=NOW,
        ),
    )
    session.commit()
    return proposal


def _execute(session: Session, result: GitHubIssueExecutorResult):
    return execute_action_proposal(
        session,
        ExecuteActionProposalCommand(DEBT_ID, PROPOSAL_A),
        TARGET,
        True,
        FakeExecutor(result),
        clock=lambda: NOW + timedelta(minutes=1),
    )


def _verify(session: Session, verifier: FakeVerifier):
    execution_id = _execution_id(session)
    return verify_action_execution(
        session,
        VerifyActionExecutionCommand(DEBT_ID, PROPOSAL_A, execution_id),
        TARGET,
        verifier,
        clock=lambda: NOW + timedelta(minutes=2),
    )


def _execution_id(session: Session) -> UUID:
    with session.begin():
        persisted = session.scalar(select(ActionExecutionModel))
        assert persisted is not None
        return persisted.action_execution_id


def _created_result() -> GitHubIssueExecutorResult:
    return GitHubIssueExecutorResult(
        outcome=GitHubIssueExecutorOutcome.CREATED,
        external_issue_id=9007,
        external_issue_number=7,
        external_issue_url=ISSUE_URL,
    )


def test_succeeded_exact_issue_passes_outside_transaction(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(session, _created_result())
        assert created.execution is not None
        verifier = FakeVerifier(session, issue=_matching_issue(proposal))

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.PASS
        assert verification.safe_reason_code is None
        assert verifier.get_calls == [("demo-owner", "demo-repository", 7)]
        assert verifier.search_calls == []
        assert session.get(TechnicalDebtModel, DEBT_ID).lifecycle_status == (
            "REGISTERED"
        )
        assert created.execution.status is ActionExecutionStatus.SUCCEEDED


def test_changed_title_fails_without_closing_debt(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        _execute(session, _created_result())
        verifier = FakeVerifier(
            session,
            issue=_matching_issue(proposal, title="Changed title"),
        )

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.FAIL
        assert (
            verification.safe_reason_code
            is ActionVerificationReasonCode.TITLE_MISMATCH
        )
        assert session.get(TechnicalDebtModel, DEBT_ID).lifecycle_status == (
            "REGISTERED"
        )


def test_changed_body_fails(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        _execute(session, _created_result())
        verifier = FakeVerifier(
            session,
            issue=_matching_issue(
                proposal,
                body=f"Changed body\n\n{proposal.reconciliation_marker}",
            ),
        )

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.FAIL
        assert (
            verification.safe_reason_code
            is ActionVerificationReasonCode.FINGERPRINT_MISMATCH
        )


def test_marker_missing_fails(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        _execute(session, _created_result())
        verifier = FakeVerifier(
            session,
            issue=_matching_issue(proposal, body="Exact body without marker"),
        )

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.FAIL
        assert (
            verification.safe_reason_code is ActionVerificationReasonCode.MARKER_MISSING
        )


def test_pull_request_response_fails(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        _execute(session, _created_result())
        verifier = FakeVerifier(
            session,
            issue=_matching_issue(proposal, is_pull_request=True),
        )

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.FAIL
        assert (
            verification.safe_reason_code is ActionVerificationReasonCode.PULL_REQUEST
        )


def test_reader_unavailable_persists_unavailable_without_status_change(engine) -> None:
    with Session(engine) as session:
        _seed(session)
        created = _execute(session, _created_result())
        verifier = FakeVerifier(
            session,
            get_outcome=GitHubIssueReadOutcome.UNAVAILABLE,
        )

        verification = _verify(session, verifier)

        assert verification.result is ActionVerificationResult.UNAVAILABLE
        assert (
            verification.safe_reason_code
            is ActionVerificationReasonCode.TRANSPORT_UNAVAILABLE
        )
        assert created.execution is not None
        reloaded = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )
        assert reloaded is not None
        assert reloaded.status == ActionExecutionStatus.SUCCEEDED.value


def test_repeated_verification_is_append_only(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        _execute(session, _created_result())
        verifier = FakeVerifier(session, issue=_matching_issue(proposal))

        first = _verify(session, verifier)
        second = _verify(session, verifier)

        assert first.action_verification_id != second.action_verification_id
        count = session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        )
        assert count == 2


def test_unknown_marker_found_promotes_to_succeeded_then_passes(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        issue = _matching_issue(proposal)
        verifier = FakeVerifier(
            session,
            issue=issue,
            search_issues=(issue,),
        )

        verification = _verify(session, verifier)
        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )

        assert verification.result is ActionVerificationResult.PASS
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.SUCCEEDED.value
        assert persisted.external_issue_number == 7
        assert persisted.external_issue_url == ISSUE_URL
        assert persisted.safe_error_category is None
        assert verifier.search_calls == [
            ("demo-owner", "demo-repository", proposal.reconciliation_marker)
        ]
        assert verifier.get_calls == [("demo-owner", "demo-repository", 7)]


def test_unknown_search_ignores_empty_body_when_exact_marker_issue_exists(
    engine,
) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        empty_body_issue = _matching_issue(proposal, number=6, body="")
        exact_marker_issue = _matching_issue(proposal, number=7)
        verifier = FakeVerifier(
            session,
            issue=exact_marker_issue,
            search_issues=(empty_body_issue, exact_marker_issue),
        )

        verification = _verify(session, verifier)
        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )

        assert verification.result is ActionVerificationResult.PASS
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.SUCCEEDED.value
        assert persisted.external_issue_number == 7
        assert persisted.external_issue_url == ISSUE_URL
        assert verifier.get_calls == [("demo-owner", "demo-repository", 7)]


def test_unknown_search_with_empty_body_only_remains_unresolved(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        verifier = FakeVerifier(
            session,
            search_issues=(_matching_issue(proposal, body=""),),
        )

        with pytest.raises(
            ActionExecutionReconciliationUnresolved,
            match="could not be reconciled",
        ):
            _verify(session, verifier)

        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.UNKNOWN.value
        assert persisted.external_issue_number is None
        assert persisted.external_issue_url is None
        assert verifier.get_calls == []


def test_unknown_marker_absent_remains_unknown_without_verification_row(engine) -> None:
    with Session(engine) as session:
        _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        verifier = FakeVerifier(
            session,
            search_outcome=GitHubIssueReadOutcome.NOT_FOUND,
        )

        with pytest.raises(
            ActionExecutionReconciliationUnresolved,
            match="could not be reconciled",
        ):
            _verify(session, verifier)

        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.UNKNOWN.value
        assert persisted.external_issue_number is None
        count = session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        )
        assert count == 0
        assert verifier.get_calls == []


def test_unknown_multiple_exact_marker_matches_remain_ambiguous(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        first = _matching_issue(proposal, number=7)
        second = _matching_issue(
            proposal,
            number=8,
            html_url="https://github.com/demo-owner/demo-repository/issues/8",
        )
        verifier = FakeVerifier(session, search_issues=(first, second))

        with pytest.raises(
            ActionExecutionReconciliationUnresolved,
            match="ambiguous",
        ):
            _verify(session, verifier)

        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.UNKNOWN.value
        assert verifier.get_calls == []


def test_in_progress_crash_window_marker_found_promotes_to_succeeded(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        with pytest.raises(KeyboardInterrupt):
            execute_action_proposal(
                session,
                ExecuteActionProposalCommand(DEBT_ID, PROPOSAL_A),
                TARGET,
                True,
                ProcessCrashExecutor(),
                clock=lambda: NOW + timedelta(minutes=1),
            )
        issue = _matching_issue(proposal)
        verifier = FakeVerifier(session, issue=issue, search_issues=(issue,))

        verification = _verify(session, verifier)
        persisted = session.get(ActionExecutionModel, _execution_id(session))

        assert verification.result is ActionVerificationResult.PASS
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.SUCCEEDED.value
        assert persisted.external_issue_number == 7


def test_failed_execution_is_not_verifiable(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(outcome=GitHubIssueExecutorOutcome.REJECTED),
        )
        verifier = FakeVerifier(session, issue=_matching_issue(proposal))

        with pytest.raises(ActionExecutionNotVerifiable):
            _verify(session, verifier)

        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )
        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.FAILED.value
        assert session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        ) == 0
        assert verifier.get_calls == []
        assert verifier.search_calls == []


def test_missing_verifier_is_unavailable_after_load(engine) -> None:
    with Session(engine) as session:
        _seed(session)
        created = _execute(session, _created_result())

        with pytest.raises(ActionVerificationUnavailable):
            verify_action_execution(
                session,
                VerifyActionExecutionCommand(
                    DEBT_ID, PROPOSAL_A, created.execution.action_execution_id
                ),
                TARGET,
                None,
            )

        assert session.scalar(
            select(func.count()).select_from(ActionVerificationModel)
        ) == 0


def test_reconcile_unknown_does_not_permit_failed_or_in_progress_source(engine) -> None:
    with Session(engine) as session:
        _seed(session)
        created = _execute(session, _created_result())
        succeeded = created.execution
        assert succeeded is not None
        with pytest.raises(ValueError, match="Only UNKNOWN"):
            reconcile_unknown_execution_success(session, succeeded)


def test_open_transaction_is_rejected(engine) -> None:
    with Session(engine) as session:
        _seed(session)
        created = _execute(session, _created_result())
        session.execute(select(ActionExecutionModel))
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            verify_action_execution(
                session,
                VerifyActionExecutionCommand(
                    DEBT_ID, PROPOSAL_A, created.execution.action_execution_id
                ),
                TARGET,
                FakeVerifier(session, issue=_matching_issue(_proposal())),
            )


def test_verification_service_never_imports_write_executor() -> None:
    source = Path(
        __import__("app.actions.verification", fromlist=["verify_action_execution"])
        .__file__
        or ""
    ).read_text(encoding="utf-8")
    assert "GitHubIssueExecutor" not in source
    assert "create_issue" not in source
    assert "client.post" not in source


def test_second_reconciliation_does_not_overwrite_reference(engine) -> None:
    with Session(engine) as session:
        proposal = _seed(session)
        created = _execute(
            session,
            GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            ),
        )
        matching = _matching_issue(proposal)
        first_verifier = FakeVerifier(
            session, issue=matching, search_issues=(matching,)
        )
        _verify(session, first_verifier)
        other = _matching_issue(
            proposal,
            number=99,
            html_url="https://github.com/demo-owner/demo-repository/issues/99",
        )
        second_verifier = FakeVerifier(session, issue=other, search_issues=(other,))

        second = _verify(session, second_verifier)
        persisted = session.get(
            ActionExecutionModel, created.execution.action_execution_id
        )

        assert persisted is not None
        assert persisted.status == ActionExecutionStatus.SUCCEEDED.value
        assert persisted.external_issue_number == 7
        assert persisted.external_issue_url == ISSUE_URL
        assert second.result is ActionVerificationResult.FAIL
        assert (
            second.safe_reason_code
            is ActionVerificationReasonCode.REFERENCE_MISMATCH
        )
