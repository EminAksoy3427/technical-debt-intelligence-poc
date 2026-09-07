from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier, Thread
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import delete, event, func, inspect, select
from sqlalchemy.orm import Session

from alembic import command
from app.actions.approval import approve_action_proposal
from app.actions.contracts import (
    ActionProposalAlreadyApproved,
    ApproveActionProposalCommand,
    CompetingActionApprovalExists,
)
from app.core.config import Settings
from app.domain.action_approvals import ActionApproval
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.signals import Evidence, Signal
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_approval_persistence import (
    technical_debt_action_approval_boundary_statement,
)
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import (
    persist_action_proposal,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.candidate_persistence import persist_candidate
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.database.enterprise_estate_seed import seed_enterprise_estate
from app.infrastructure.database.human_decision_models import HumanDecisionModel
from app.infrastructure.database.human_decision_persistence import (
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.signal_persistence import persist_normalized_signal
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel
from app.infrastructure.database.technical_debt_persistence import (
    persist_technical_debt,
)
from app.signal_ingestion import NormalizedSignal

EXPECTED_HEAD = "20260907_03"
ACTOR = HumanActorContext(actor_reference="poc:local-reviewer")


def _unique_column_sets(inspector: object, table_name: str) -> set[frozenset[str]]:
    unique_indexes = {
        frozenset(index["column_names"])
        for index in inspector.get_indexes(table_name)  # type: ignore[attr-defined]
        if index.get("unique")
    }
    try:
        unique_constraints = {
            frozenset(constraint["column_names"])
            for constraint in inspector.get_unique_constraints(table_name)  # type: ignore[attr-defined]
        }
    except NotImplementedError:
        unique_constraints = set()
    return unique_constraints | unique_indexes


def _foreign_key_targets(inspector: object, table_name: str) -> set[str]:
    return {
        foreign_key["referred_table"]
        for foreign_key in inspector.get_foreign_keys(table_name)  # type: ignore[attr-defined]
    }


def _nullable_columns(inspector: object, table_name: str) -> set[str]:
    return {
        column["name"]
        for column in inspector.get_columns(table_name)  # type: ignore[attr-defined]
        if column["nullable"]
    }


def _proposal(
    *,
    action_proposal_id: UUID,
    technical_debt_id: UUID,
) -> ActionProposal:
    marker = action_proposal_reconciliation_marker(action_proposal_id)
    payload = GitHubIssuePayload(
        title="Technical debt: repo-borealis-renderer",
        body=f"Technical debt remediation tracking issue\n\n{marker}\n",
    )
    return ActionProposal(
        action_proposal_id=action_proposal_id,
        technical_debt_id=technical_debt_id,
        action_type=ActionType.CREATE_GITHUB_ISSUE,
        target_repository_owner="tdi-demo-target",
        target_repository_name="tdi-action-preview",
        payload=payload,
        payload_fingerprint=canonical_action_payload_fingerprint(
            action_type=ActionType.CREATE_GITHUB_ISSUE.value,
            target_repository_owner="tdi-demo-target",
            target_repository_name="tdi-action-preview",
            title=payload.title,
            body=payload.body,
        ),
        reconciliation_marker=marker,
        prepared_by="poc:local-reviewer",
        created_at=datetime(2026, 9, 7, 20, 0, tzinfo=UTC),
    )


def _seed_registered_debt(
    session: Session,
    *,
    candidate_id: UUID,
    signal_id: UUID,
    evidence_id: UUID,
    decision_id: UUID,
    technical_debt_id: UUID,
    source_record: str,
) -> None:
    timestamp = datetime(2026, 9, 7, 20, 0, tzinfo=UTC)
    persist_normalized_signal(
        session,
        NormalizedSignal(
            signal=Signal(
                signal_id=signal_id,
                source_system="mssql-action-approval-integration-test",
                source_record_id=source_record,
                detected_at=timestamp,
                signal_type="MISSING_TIMEOUT",
                affected_asset=CanonicalAssetRef(
                    asset_key="repo-borealis-renderer",
                    asset_type=AssetType.REPOSITORY,
                ),
                severity="MEDIUM",
                evidence_ids=frozenset({evidence_id}),
            ),
            evidence=frozenset(
                {
                    Evidence(
                        evidence_id=evidence_id,
                        source_system="mssql-action-approval-integration-test",
                        source_reference=source_record,
                        captured_at=timestamp,
                    )
                }
            ),
        ),
    )
    persist_candidate(
        session,
        Candidate(
            candidate_id=candidate_id,
            signal_ids=frozenset({signal_id}),
            evidence_ids=frozenset({evidence_id}),
            canonical_asset=CanonicalAssetRef(
                asset_key="repo-borealis-renderer",
                asset_type=AssetType.REPOSITORY,
            ),
            hypothesis="Potential missing request timeout",
            correlation_rationale=(
                "Signal shares the Candidate asset and problem family."
            ),
        ),
    )
    persist_human_decision(
        session,
        HumanDecision(
            human_decision_id=decision_id,
            candidate_id=candidate_id,
            sequence_number=1,
            decision_type=HumanDecisionType.VALIDATE,
            rationale="The Candidate is a validated structural issue.",
            requested_information=None,
            actor_reference="poc:local-reviewer",
            created_at=timestamp,
        ),
    )
    persist_technical_debt(
        session,
        TechnicalDebt(
            technical_debt_id=technical_debt_id,
            source_candidate_id=candidate_id,
            creation_human_decision_id=decision_id,
            lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
            created_at=timestamp,
        ),
    )


def _cleanup(
    session: Session,
    *,
    technical_debt_ids: tuple[UUID, ...],
    proposal_ids: tuple[UUID, ...],
    candidate_ids: tuple[UUID, ...],
    decision_ids: tuple[UUID, ...],
    evidence_ids: tuple[UUID, ...],
    signal_ids: tuple[UUID, ...],
) -> None:
    session.execute(
        delete(ActionApprovalModel).where(
            ActionApprovalModel.action_proposal_id.in_(proposal_ids)
        )
    )
    session.execute(
        delete(ActionProposalModel).where(
            ActionProposalModel.action_proposal_id.in_(proposal_ids)
        )
    )
    session.execute(
        delete(TechnicalDebtModel).where(
            TechnicalDebtModel.technical_debt_id.in_(technical_debt_ids)
        )
    )
    session.execute(
        delete(HumanDecisionModel).where(
            HumanDecisionModel.human_decision_id.in_(decision_ids)
        )
    )
    session.execute(
        delete(CandidateSignalModel).where(
            CandidateSignalModel.candidate_id.in_(candidate_ids)
        )
    )
    session.execute(
        delete(CandidateModel).where(CandidateModel.candidate_id.in_(candidate_ids))
    )
    session.execute(
        delete(EvidenceModel).where(EvidenceModel.evidence_id.in_(evidence_ids))
    )
    session.execute(delete(SignalModel).where(SignalModel.signal_id.in_(signal_ids)))
    session.commit()


@pytest.mark.integration
def test_mssql_migrates_action_approval_and_policy_schema() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    try:
        inspector = inspect(engine)
        assert {"action_approvals", "action_policy_decisions"} <= set(
            inspector.get_table_names()
        )
        assert _foreign_key_targets(inspector, "action_approvals") == {
            "action_proposals"
        }
        assert _foreign_key_targets(inspector, "action_policy_decisions") == {
            "action_proposals",
            "action_approvals",
        }
        assert frozenset({"action_proposal_id"}) in _unique_column_sets(
            inspector,
            "action_approvals",
        )
        assert frozenset({"technical_debt_id", "action_type"}) not in (
            _unique_column_sets(inspector, "action_approvals")
        )
        assert frozenset({"action_proposal_id"}) not in _unique_column_sets(
            inspector,
            "action_policy_decisions",
        )
        required_approval = {
            "action_approval_id",
            "action_proposal_id",
            "payload_fingerprint",
            "actor_reference",
            "created_at",
        }
        assert required_approval.isdisjoint(
            _nullable_columns(inspector, "action_approvals")
        )
        assert "action_approval_id" in _nullable_columns(
            inspector,
            "action_policy_decisions",
        )
        technical_debt_columns = {
            column["name"] for column in inspector.get_columns("technical_debts")
        }
        assert technical_debt_columns == {
            "technical_debt_id",
            "source_candidate_id",
            "creation_human_decision_id",
            "lifecycle_status",
            "created_at",
        }
        proposal_columns = {
            column["name"] for column in inspector.get_columns("action_proposals")
        }
        assert "approved" not in proposal_columns

        with engine.connect() as connection:
            assert MigrationContext.configure(connection).get_current_revision() == (
                EXPECTED_HEAD
            )
    finally:
        engine.dispose()


@pytest.mark.integration
def test_mssql_serializes_cross_proposal_approvals_to_one_winner() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    captured_sql: list[str] = []

    def capture_sql(
        _conn: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: object,
    ) -> None:
        captured_sql.append(statement)

    event.listen(engine, "before_cursor_execute", capture_sql)
    candidate_id = uuid4()
    signal_id = uuid4()
    evidence_id = uuid4()
    decision_id = uuid4()
    technical_debt_id = uuid4()
    proposal_a_id = uuid4()
    proposal_b_id = uuid4()
    barrier = Barrier(2)
    outcomes: list[ActionApproval | BaseException] = []

    def worker(proposal: ActionProposal) -> None:
        try:
            with Session(engine) as session:
                barrier.wait(timeout=10)
                result = approve_action_proposal(
                    session,
                    ApproveActionProposalCommand(
                        technical_debt_id=technical_debt_id,
                        action_proposal_id=proposal.action_proposal_id,
                        expected_payload_fingerprint=proposal.payload_fingerprint,
                    ),
                    ACTOR,
                    clock=lambda: datetime(2026, 9, 7, 20, 1, tzinfo=UTC),
                )
                outcomes.append(result)
        except BaseException as error:
            outcomes.append(error)

    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            _seed_registered_debt(
                session,
                candidate_id=candidate_id,
                signal_id=signal_id,
                evidence_id=evidence_id,
                decision_id=decision_id,
                technical_debt_id=technical_debt_id,
                source_record=f"signal-{candidate_id}",
            )
            persist_action_proposal(
                session,
                _proposal(
                    action_proposal_id=proposal_a_id,
                    technical_debt_id=technical_debt_id,
                ),
            )
            persist_action_proposal(
                session,
                _proposal(
                    action_proposal_id=proposal_b_id,
                    technical_debt_id=technical_debt_id,
                ),
            )
            session.commit()

        proposal_a = _proposal(
            action_proposal_id=proposal_a_id,
            technical_debt_id=technical_debt_id,
        )
        proposal_b = _proposal(
            action_proposal_id=proposal_b_id,
            technical_debt_id=technical_debt_id,
        )
        first = Thread(target=worker, args=(proposal_a,))
        second = Thread(target=worker, args=(proposal_b,))
        first.start()
        second.start()
        first.join(timeout=30)
        second.join(timeout=30)
        assert not first.is_alive()
        assert not second.is_alive()

        successes = [item for item in outcomes if isinstance(item, ActionApproval)]
        conflicts = [
            item
            for item in outcomes
            if isinstance(
                item,
                (CompetingActionApprovalExists, ActionProposalAlreadyApproved),
            )
        ]
        assert len(outcomes) == 2
        assert len(successes) == 1
        assert len(conflicts) == 1

        lock_sql = str(
            technical_debt_action_approval_boundary_statement(
                technical_debt_id
            ).compile(dialect=engine.dialect)
        )
        assert "UPDLOCK" in lock_sql
        assert "HOLDLOCK" in lock_sql
        assert any(
            "UPDLOCK" in statement and "HOLDLOCK" in statement
            for statement in captured_sql
        )

        with Session(engine) as session:
            approval_count = session.scalar(
                select(func.count())
                .select_from(ActionApprovalModel)
                .join(
                    ActionProposalModel,
                    ActionApprovalModel.action_proposal_id
                    == ActionProposalModel.action_proposal_id,
                )
                .where(ActionProposalModel.technical_debt_id == technical_debt_id)
            )
            assert approval_count == 1
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)
        with Session(engine) as session:
            _cleanup(
                session,
                technical_debt_ids=(technical_debt_id,),
                proposal_ids=(proposal_a_id, proposal_b_id),
                candidate_ids=(candidate_id,),
                decision_ids=(decision_id,),
                evidence_ids=(evidence_id,),
                signal_ids=(signal_id,),
            )
        engine.dispose()


@pytest.mark.integration
def test_mssql_allows_approvals_for_different_technical_debts() -> None:
    app_settings = Settings()
    if app_settings.database_url is None:
        pytest.skip("DATABASE_URL is not configured")

    backend_root = Path(__file__).resolve().parents[2]
    command.upgrade(Config(str(backend_root / "alembic.ini")), "head")
    engine = create_database_engine(app_settings)
    first_ids = {
        "candidate": uuid4(),
        "signal": uuid4(),
        "evidence": uuid4(),
        "decision": uuid4(),
        "debt": uuid4(),
        "proposal": uuid4(),
    }
    second_ids = {
        "candidate": uuid4(),
        "signal": uuid4(),
        "evidence": uuid4(),
        "decision": uuid4(),
        "debt": uuid4(),
        "proposal": uuid4(),
    }
    barrier = Barrier(2)
    outcomes: list[ActionApproval | BaseException] = []

    def worker(technical_debt_id: UUID, proposal: ActionProposal) -> None:
        try:
            with Session(engine) as session:
                barrier.wait(timeout=10)
                result = approve_action_proposal(
                    session,
                    ApproveActionProposalCommand(
                        technical_debt_id=technical_debt_id,
                        action_proposal_id=proposal.action_proposal_id,
                        expected_payload_fingerprint=proposal.payload_fingerprint,
                    ),
                    ACTOR,
                    clock=lambda: datetime(2026, 9, 7, 20, 2, tzinfo=UTC),
                )
                outcomes.append(result)
        except BaseException as error:
            outcomes.append(error)

    try:
        with Session(engine) as session:
            seed_enterprise_estate(session)
            for ids, source in (
                (first_ids, "first"),
                (second_ids, "second"),
            ):
                _seed_registered_debt(
                    session,
                    candidate_id=ids["candidate"],
                    signal_id=ids["signal"],
                    evidence_id=ids["evidence"],
                    decision_id=ids["decision"],
                    technical_debt_id=ids["debt"],
                    source_record=f"signal-{ids['candidate']}-{source}",
                )
                persist_action_proposal(
                    session,
                    _proposal(
                        action_proposal_id=ids["proposal"],
                        technical_debt_id=ids["debt"],
                    ),
                )
            session.commit()

        first_proposal = _proposal(
            action_proposal_id=first_ids["proposal"],
            technical_debt_id=first_ids["debt"],
        )
        second_proposal = _proposal(
            action_proposal_id=second_ids["proposal"],
            technical_debt_id=second_ids["debt"],
        )
        first = Thread(target=worker, args=(first_ids["debt"], first_proposal))
        second = Thread(target=worker, args=(second_ids["debt"], second_proposal))
        first.start()
        second.start()
        first.join(timeout=30)
        second.join(timeout=30)
        assert not first.is_alive()
        assert not second.is_alive()

        successes = [item for item in outcomes if isinstance(item, ActionApproval)]
        assert len(outcomes) == 2
        assert len(successes) == 2
        assert {item.action_proposal_id for item in successes} == {
            first_ids["proposal"],
            second_ids["proposal"],
        }
    finally:
        with Session(engine) as session:
            _cleanup(
                session,
                technical_debt_ids=(first_ids["debt"], second_ids["debt"]),
                proposal_ids=(first_ids["proposal"], second_ids["proposal"]),
                candidate_ids=(first_ids["candidate"], second_ids["candidate"]),
                decision_ids=(first_ids["decision"], second_ids["decision"]),
                evidence_ids=(first_ids["evidence"], second_ids["evidence"]),
                signal_ids=(first_ids["signal"], second_ids["signal"]),
            )
        engine.dispose()
