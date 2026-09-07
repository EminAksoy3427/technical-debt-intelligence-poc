from pathlib import Path
from threading import Barrier, Lock, Thread
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import delete, func, inspect, select, text
from sqlalchemy.orm import Session

from alembic import command
from app.actions.contracts import (
    ActionPreparationContext,
    ExecuteActionProposalCommand,
    LogicalActionExecutionConflict,
)
from app.actions.execution import (
    ExecuteActionProposalDisposition,
    ExecuteActionProposalResult,
    execute_action_proposal,
)
from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)
from app.core.config import Settings
from app.domain.action_approvals import ActionApproval
from app.infrastructure.database.action_approval_persistence import (
    persist_action_approval,
)
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from tests.integration.test_mssql_action_approval_persistence import (
    _cleanup,
    _proposal,
    _seed_registered_debt,
)

TARGET = ActionPreparationContext("tdi-demo-target", "tdi-action-preview")


class ThreadSafeExecutor:
    def __init__(self, call_barrier: Barrier | None = None) -> None:
        self._lock = Lock()
        self._call_barrier = call_barrier
        self.commands: list[CreateGitHubIssueCommand] = []

    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
        with self._lock:
            self.commands.append(command)
            issue_number = len(self.commands)
        if self._call_barrier is not None:
            self._call_barrier.wait(timeout=10)
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.CREATED,
            external_issue_id=10_000 + issue_number,
            external_issue_number=issue_number,
            external_issue_url=f"https://github.example/issues/{issue_number}",
        )


def _ids() -> dict[str, UUID]:
    return {
        "candidate": uuid4(),
        "signal": uuid4(),
        "evidence": uuid4(),
        "decision": uuid4(),
        "debt": uuid4(),
        "proposal": uuid4(),
    }


def _seed_chain(session: Session, ids: dict[str, UUID]) -> None:
    _seed_registered_debt(
        session,
        candidate_id=ids["candidate"],
        signal_id=ids["signal"],
        evidence_id=ids["evidence"],
        decision_id=ids["decision"],
        technical_debt_id=ids["debt"],
        source_record=f"execution-{ids['signal']}",
    )
    proposal = _proposal(
        action_proposal_id=ids["proposal"],
        technical_debt_id=ids["debt"],
    )
    persist_action_proposal(session, proposal)
    persist_action_approval(
        session,
        ActionApproval(
            action_approval_id=uuid4(),
            action_proposal_id=proposal.action_proposal_id,
            payload_fingerprint=proposal.payload_fingerprint,
            actor_reference="poc:local-reviewer",
            created_at=proposal.created_at,
        ),
    )


def _cleanup_chains(engine, chains: tuple[dict[str, UUID], ...]) -> None:
    proposal_ids = tuple(item["proposal"] for item in chains)
    with Session(engine) as session:
        session.execute(
            delete(ActionExecutionModel).where(
                ActionExecutionModel.action_proposal_id.in_(proposal_ids)
            )
        )
        session.execute(
            delete(ActionPolicyDecisionModel).where(
                ActionPolicyDecisionModel.action_proposal_id.in_(proposal_ids)
            )
        )
        session.commit()
        _cleanup(
            session,
            technical_debt_ids=tuple(item["debt"] for item in chains),
            proposal_ids=proposal_ids,
            candidate_ids=tuple(item["candidate"] for item in chains),
            decision_ids=tuple(item["decision"] for item in chains),
            evidence_ids=tuple(item["evidence"] for item in chains),
            signal_ids=tuple(item["signal"] for item in chains),
        )


def _run_concurrently(engine, calls, executor):
    start = Barrier(len(calls))
    outcomes: list[ExecuteActionProposalResult | BaseException] = []
    outcomes_lock = Lock()

    def worker(technical_debt_id: UUID, proposal_id: UUID) -> None:
        try:
            with Session(engine) as session:
                start.wait(timeout=10)
                result = execute_action_proposal(
                    session,
                    ExecuteActionProposalCommand(technical_debt_id, proposal_id),
                    TARGET,
                    True,
                    executor,
                )
            outcome: ExecuteActionProposalResult | BaseException = result
        except BaseException as error:
            outcome = error
        with outcomes_lock:
            outcomes.append(outcome)

    threads = [Thread(target=worker, args=call) for call in calls]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)
        assert not thread.is_alive()
    return outcomes


@pytest.mark.integration
def test_mssql_action_execution_schema_and_filtered_occupancy() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        inspector = inspect(engine)
        assert "action_executions" in inspector.get_table_names()
        indexes = {
            item["name"]: item
            for item in inspector.get_indexes("action_executions")
        }
        assert indexes["uq_action_executions_live_logical_action"]["unique"]
        with engine.connect() as connection:
            assert (
                MigrationContext.configure(connection).get_current_revision()
                == "20260907_03"
            )
            filter_definition = connection.execute(
                text(
                    "SELECT filter_definition FROM sys.indexes "
                    "WHERE name = 'uq_action_executions_live_logical_action'"
                )
            ).scalar_one()
            assert "IN_PROGRESS" in filter_definition
            assert "SUCCEEDED" in filter_definition
            assert "UNKNOWN" in filter_definition
            assert "FAILED" not in filter_definition
    finally:
        engine.dispose()


@pytest.mark.integration
def test_mssql_concurrent_same_proposal_posts_once() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    chain = _ids()
    executor = ThreadSafeExecutor()
    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            _seed_chain(session, chain)
            session.commit()
        outcomes = _run_concurrently(
            engine,
            ((chain["debt"], chain["proposal"]),) * 2,
            executor,
        )
        assert len(executor.commands) == 1
        results = [
            item
            for item in outcomes
            if isinstance(item, ExecuteActionProposalResult)
        ]
        assert len(results) == 2
        assert {item.disposition for item in results} == {
            ExecuteActionProposalDisposition.CREATED,
            ExecuteActionProposalDisposition.EXISTING,
        }
        with Session(engine) as session:
            count = session.scalar(
                select(func.count()).select_from(ActionExecutionModel).where(
                    ActionExecutionModel.action_proposal_id == chain["proposal"]
                )
            )
            assert count == 1
    finally:
        _cleanup_chains(engine, (chain,))
        engine.dispose()


@pytest.mark.integration
def test_mssql_concurrent_different_proposals_same_debt_has_one_winner() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    first = _ids()
    second = {
        **_ids(),
        "debt": first["debt"],
        "candidate": first["candidate"],
        "signal": first["signal"],
        "evidence": first["evidence"],
        "decision": first["decision"],
    }
    executor = ThreadSafeExecutor()
    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            _seed_chain(session, first)
            proposal = _proposal(
                action_proposal_id=second["proposal"],
                technical_debt_id=first["debt"],
            )
            persist_action_proposal(session, proposal)
            persist_action_approval(
                session,
                ActionApproval(
                    action_approval_id=uuid4(),
                    action_proposal_id=proposal.action_proposal_id,
                    payload_fingerprint=proposal.payload_fingerprint,
                    actor_reference="poc:local-reviewer",
                    created_at=proposal.created_at,
                ),
            )
            session.commit()
        outcomes = _run_concurrently(
            engine,
            (
                (first["debt"], first["proposal"]),
                (first["debt"], second["proposal"]),
            ),
            executor,
        )
        assert len(executor.commands) == 1
        successes = sum(
            isinstance(item, ExecuteActionProposalResult) for item in outcomes
        )
        conflicts = sum(
            isinstance(item, LogicalActionExecutionConflict) for item in outcomes
        )
        assert successes == 1
        assert conflicts == 1
    finally:
        _cleanup_chains(engine, (first, second))
        engine.dispose()


@pytest.mark.integration
def test_mssql_concurrent_different_debts_execute_independently() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")
    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    first = _ids()
    second = _ids()
    executor = ThreadSafeExecutor(call_barrier=Barrier(2))
    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            _seed_chain(session, first)
            _seed_chain(session, second)
            session.commit()
        outcomes = _run_concurrently(
            engine,
            (
                (first["debt"], first["proposal"]),
                (second["debt"], second["proposal"]),
            ),
            executor,
        )
        assert len(executor.commands) == 2
        assert all(isinstance(item, ExecuteActionProposalResult) for item in outcomes)
    finally:
        _cleanup_chains(engine, (first, second))
        engine.dispose()
