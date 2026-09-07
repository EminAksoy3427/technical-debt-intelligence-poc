from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.orm import Session

from app.actions.contracts import ActionPreparationContext
from app.actions.execution_policy import (
    evaluate_persisted_action_execution_policy,
    record_action_execution_policy_decision,
)
from app.domain.action_approvals import ActionApproval
from app.domain.action_policy import ActionPolicyOutcome, ActionPolicyReasonCode
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.infrastructure.database.action_approval_persistence import (
    persist_action_approval,
)
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
from app.infrastructure.database.action_policy_persistence import (
    list_action_policy_decisions_for_proposal,
)
from app.infrastructure.database.action_proposal_persistence import (
    load_action_proposal,
    persist_action_proposal,
)
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_persistence import (
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.technical_debt_persistence import (
    persist_technical_debt,
)

CREATED_AT = datetime(2026, 9, 7, 19, 30, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")
ALLOWED = ActionPreparationContext(
    target_repository_owner="tdi-demo-target",
    target_repository_name="tdi-action-preview",
)


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    backend_root = Path(__file__).resolve().parents[3]
    scripts = ScriptDirectory.from_config(Config(str(backend_root / "alembic.ini")))
    revisions = list(scripts.walk_revisions(base="base", head="heads"))
    with engine.begin() as connection:
        operations = Operations(MigrationContext.configure(connection))
        for revision in reversed(revisions):
            monkeypatch.setattr(revision.module, "op", operations, raising=False)
            revision.module.upgrade()

    with Session(engine) as session:
        asset = EnterpriseAssetModel(
            asset_key="repo-borealis-renderer",
            asset_type="REPOSITORY",
            name="Borealis Renderer Repository",
            criticality="MEDIUM",
            lifecycle_status="ACTIVE",
        )
        signal = SignalModel(
            signal_id=uuid4(),
            source_system="action-policy-persistence-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="action-policy-persistence-test",
                    source_reference="source-721",
                    captured_at=CREATED_AT,
                )
            ],
        )
        session.add(
            CandidateModel(
                candidate_id=CANDIDATE_ID,
                canonical_asset=asset,
                hypothesis="Potential missing request timeout",
                correlation_rationale=(
                    "Persisted Signals share an asset and problem family."
                ),
                signal_memberships=[CandidateSignalModel(signal=signal)],
            )
        )
        persist_human_decision(
            session,
            HumanDecision(
                human_decision_id=DECISION_ID,
                candidate_id=CANDIDATE_ID,
                sequence_number=1,
                decision_type=HumanDecisionType.VALIDATE,
                rationale="The Candidate is a validated structural issue.",
                requested_information=None,
                actor_reference="poc:local-reviewer",
                created_at=CREATED_AT,
            ),
        )
        persist_technical_debt(
            session,
            TechnicalDebt(
                technical_debt_id=TECHNICAL_DEBT_ID,
                source_candidate_id=CANDIDATE_ID,
                creation_human_decision_id=DECISION_ID,
                lifecycle_status=TechnicalDebtLifecycleStatus.REGISTERED,
                created_at=CREATED_AT,
            ),
        )
        persist_action_proposal(session, _proposal())
        session.commit()

    yield engine
    engine.dispose()


def _proposal() -> ActionProposal:
    marker = action_proposal_reconciliation_marker(PROPOSAL_ID)
    payload = GitHubIssuePayload(
        title="Technical debt: repo-borealis-renderer",
        body=f"Technical debt remediation tracking issue\n\n{marker}\n",
    )
    return ActionProposal(
        action_proposal_id=PROPOSAL_ID,
        technical_debt_id=TECHNICAL_DEBT_ID,
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
        created_at=CREATED_AT,
    )


def _approval() -> ActionApproval:
    return ActionApproval(
        action_approval_id=APPROVAL_ID,
        action_proposal_id=PROPOSAL_ID,
        payload_fingerprint=_proposal().payload_fingerprint,
        actor_reference="poc:local-reviewer",
        created_at=CREATED_AT,
    )


def test_missing_approval_records_deny(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        decision = record_action_execution_policy_decision(
            session,
            proposal,
            None,
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.decision is ActionPolicyOutcome.DENY
    assert decision.reason_code is ActionPolicyReasonCode.APPROVAL_MISSING
    assert decision.action_approval_id is None


def test_allow_records_when_trusted_conditions_hold(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        decision = record_action_execution_policy_decision(
            session,
            proposal,
            _approval(),
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.decision is ActionPolicyOutcome.ALLOW
    assert decision.reason_code is ActionPolicyReasonCode.POLICY_ALLOWED
    assert decision.action_approval_id == APPROVAL_ID


def test_execution_disabled_records_deny_even_with_approval(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        decision = record_action_execution_policy_decision(
            session,
            proposal,
            _approval(),
            ALLOWED,
            False,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.reason_code is ActionPolicyReasonCode.EXECUTION_DISABLED


def test_repository_mismatch_records_deny(database_engine: Engine) -> None:
    other_target = ActionPreparationContext(
        target_repository_owner="other-owner",
        target_repository_name="other-repo",
    )
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        decision = record_action_execution_policy_decision(
            session,
            proposal,
            _approval(),
            other_target,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.reason_code is ActionPolicyReasonCode.REPOSITORY_NOT_ALLOWLISTED


def test_fingerprint_mismatch_records_deny(database_engine: Engine) -> None:
    mismatched = ActionApproval(
        action_approval_id=APPROVAL_ID,
        action_proposal_id=PROPOSAL_ID,
        payload_fingerprint="b" * 64,
        actor_reference="poc:local-reviewer",
        created_at=CREATED_AT,
    )
    with Session(database_engine) as session:
        persist_action_approval(session, mismatched)
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        decision = record_action_execution_policy_decision(
            session,
            proposal,
            mismatched,
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.reason_code is ActionPolicyReasonCode.FINGERPRINT_MISMATCH
    assert decision.action_approval_id == APPROVAL_ID


def test_multiple_policy_evaluations_are_append_only(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        first = record_action_execution_policy_decision(
            session,
            proposal,
            None,
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
            new_id=lambda: UUID("00000000-0000-0000-0000-000000000701"),
        )
        persist_action_approval(session, _approval())
        second = record_action_execution_policy_decision(
            session,
            proposal,
            _approval(),
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
            new_id=lambda: UUID("00000000-0000-0000-0000-000000000702"),
        )
        session.commit()

    with Session(database_engine) as session:
        history = list_action_policy_decisions_for_proposal(session, PROPOSAL_ID)
        count = session.scalar(
            select(func.count()).select_from(ActionPolicyDecisionModel)
        )

    assert count == 2
    assert [item.action_policy_decision_id for item in history] == [
        first.action_policy_decision_id,
        second.action_policy_decision_id,
    ]
    assert history[0].reason_code is ActionPolicyReasonCode.APPROVAL_MISSING
    assert history[1].reason_code is ActionPolicyReasonCode.POLICY_ALLOWED


def test_persisted_evaluator_loads_server_owned_facts(database_engine: Engine) -> None:
    with Session(database_engine) as session:
        persist_action_approval(session, _approval())
        session.commit()

    with Session(database_engine) as session:
        decision = evaluate_persisted_action_execution_policy(
            session,
            PROPOSAL_ID,
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        session.commit()

    assert decision.decision is ActionPolicyOutcome.ALLOW


def test_policy_helper_does_not_commit(database_engine: Engine) -> None:
    committed = False

    def mark_commit(_session: Session) -> None:
        nonlocal committed
        committed = True

    with Session(database_engine) as session:
        event.listen(session, "before_commit", mark_commit)
        proposal = load_action_proposal(session, PROPOSAL_ID)
        assert proposal is not None
        record_action_execution_policy_decision(
            session,
            proposal,
            None,
            ALLOWED,
            True,
            executor_ready=True,
            clock=lambda: CREATED_AT,
        )
        assert committed is False
