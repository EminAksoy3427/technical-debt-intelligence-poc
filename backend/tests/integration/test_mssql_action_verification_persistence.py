from pathlib import Path
from threading import Barrier, Lock, Thread
from uuid import UUID

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.actions.contracts import (
    ExecuteActionProposalCommand,
    VerifyActionExecutionCommand,
)
from app.actions.execution import execute_action_proposal
from app.actions.github_issue_executor import (
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
from app.core.config import Settings
from app.domain.action_verifications import ActionVerification
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_proposal_persistence import load_action_proposal
from app.infrastructure.database.action_verification_models import (
    ActionVerificationModel,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from tests.integration.test_mssql_action_execution_persistence import (
    TARGET,
    _cleanup_chains,
    _ids,
    _seed_chain,
)

ISSUE_URL = "https://github.com/tdi-demo-target/tdi-action-preview/issues/7"


class ThreadSafeVerifier:
    def __init__(self, issue: ObservedGitHubIssue) -> None:
        self._lock = Lock()
        self.issue = issue
        self.get_calls = 0
        self.search_calls = 0
        self.post_calls = 0

    def get_issue(
        self,
        owner: str,
        repository: str,
        issue_number: int,
    ) -> GitHubIssueReadResult:
        with self._lock:
            self.get_calls += 1
        return GitHubIssueReadResult(
            outcome=GitHubIssueReadOutcome.FOUND,
            issue=self.issue,
        )

    def find_issues_by_marker(
        self,
        owner: str,
        repository: str,
        marker: str,
    ) -> GitHubIssueSearchResult:
        with self._lock:
            self.search_calls += 1
        return GitHubIssueSearchResult(
            outcome=GitHubIssueReadOutcome.FOUND,
            issues=(self.issue,),
        )

    def create_issue(self, command: object) -> None:
        with self._lock:
            self.post_calls += 1
        raise AssertionError("Verification must never POST")


@pytest.mark.integration
def test_mssql_action_verification_schema() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        inspector = inspect(engine)
        assert "action_verifications" in inspector.get_table_names()
        columns = {
            item["name"] for item in inspector.get_columns("action_verifications")
        }
        assert columns == {
            "action_verification_id",
            "action_execution_id",
            "result",
            "observed_issue_number",
            "observed_issue_url",
            "safe_reason_code",
            "created_at",
        }
        foreign_keys = inspector.get_foreign_keys("action_verifications")
        assert {item["referred_table"] for item in foreign_keys} == {
            "action_executions"
        }
        with engine.connect() as connection:
            assert (
                MigrationContext.configure(connection).get_current_revision()
                == "20260907_04"
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_mssql_concurrent_unknown_reconcile_is_safe() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    chain = _ids()
    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            _seed_chain(session, chain)
            session.commit()
        with Session(engine) as session:
            execute_action_proposal(
                session,
                ExecuteActionProposalCommand(chain["debt"], chain["proposal"]),
                TARGET,
                True,
                _UnknownExecutor(),
            )
            proposal = load_action_proposal(session, chain["proposal"])
            assert proposal is not None
        issue = ObservedGitHubIssue(
            issue_id=7001,
            issue_number=7,
            html_url=ISSUE_URL,
            title=proposal.payload.title,
            body=proposal.payload.body,
            is_pull_request=False,
        )
        verifier = ThreadSafeVerifier(issue)
        start = Barrier(2)
        outcomes: list[ActionVerification | BaseException] = []
        outcomes_lock = Lock()

        def worker() -> None:
            try:
                with Session(engine) as session:
                    start.wait(timeout=10)
                    result = verify_action_execution(
                        session,
                        VerifyActionExecutionCommand(
                            chain["debt"],
                            chain["proposal"],
                            _execution_id(engine, chain["proposal"]),
                        ),
                        TARGET,
                        verifier,
                    )
                outcome: ActionVerification | BaseException = result
            except BaseException as error:
                outcome = error
            with outcomes_lock:
                outcomes.append(outcome)

        threads = [Thread(target=worker), Thread(target=worker)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)
            assert not thread.is_alive()

        assert verifier.post_calls == 0
        assert verifier.search_calls >= 1
        successes = [
            item for item in outcomes if isinstance(item, ActionVerification)
        ]
        assert len(successes) == 2
        with Session(engine) as session:
            execution = session.scalar(
                select(ActionExecutionModel).where(
                    ActionExecutionModel.action_proposal_id == chain["proposal"]
                )
            )
            assert execution is not None
            assert execution.status == "SUCCEEDED"
            assert execution.external_issue_number == 7
            assert execution.external_issue_url == ISSUE_URL
            count = session.scalar(
                select(func.count()).select_from(ActionVerificationModel).where(
                    ActionVerificationModel.action_execution_id
                    == execution.action_execution_id
                )
            )
            assert count == 2
    finally:
        with Session(engine) as session:
            execution_ids = select(ActionExecutionModel.action_execution_id).where(
                ActionExecutionModel.action_proposal_id == chain["proposal"]
            )
            session.execute(
                delete(ActionVerificationModel).where(
                    ActionVerificationModel.action_execution_id.in_(execution_ids)
                )
            )
            session.commit()
        _cleanup_chains(engine, (chain,))
        engine.dispose()


class _UnknownExecutor:
    def create_issue(self, command: object) -> GitHubIssueExecutorResult:
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
        )


def _execution_id(engine, proposal_id: UUID) -> UUID:
    with Session(engine) as session:
        persisted = session.scalar(
            select(ActionExecutionModel).where(
                ActionExecutionModel.action_proposal_id == proposal_id
            )
        )
        assert persisted is not None
        return persisted.action_execution_id
