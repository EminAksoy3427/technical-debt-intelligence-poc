import ast
import inspect
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.composition import (
    compose_github_issue_body,
    compose_github_issue_title,
)
from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalPersistenceConflict,
    PrepareActionProposalCommand,
    TechnicalDebtNotFound,
    TechnicalDebtNotRegistered,
)
from app.actions.preparation import (
    map_action_proposal_integrity_error,
    prepare_action_proposal,
)
from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    action_proposal_reconciliation_marker,
    canonical_action_payload_fingerprint,
)
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.action_proposal_persistence import load_action_proposal
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.candidate_persistence import load_candidate
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.human_decision_persistence import (
    persist_human_decision,
)
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.infrastructure.database.technical_debt_persistence import (
    load_technical_debt,
    persist_technical_debt,
)

CREATED_AT = datetime(2026, 9, 7, 14, 30, tzinfo=UTC)
CANDIDATE_ID = UUID("00000000-0000-0000-0000-000000000721")
TECHNICAL_DEBT_ID = UUID("00000000-0000-0000-0000-000000000911")
DECISION_ID = UUID("00000000-0000-0000-0000-000000000811")
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
SECOND_PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000502")
ACTOR = HumanActorContext(actor_reference="poc:local-reviewer")
PREPARATION = ActionPreparationContext(
    target_repository_owner="tdi-demo-target",
    target_repository_name="tdi-action-preview",
)
BACKEND_ROOT = Path(__file__).resolve().parents[2]
ACTIONS_DIR = BACKEND_ROOT / "app" / "actions"


@pytest.fixture
def database_engine(monkeypatch: pytest.MonkeyPatch) -> Iterator[Engine]:
    engine = create_engine("sqlite+pysqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(
        dbapi_connection: object,
        _connection_record: object,
    ) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")  # type: ignore[attr-defined]

    scripts = ScriptDirectory.from_config(Config(str(BACKEND_ROOT / "alembic.ini")))
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
            source_system="action-proposal-test",
            source_record_id="source-721",
            detected_at=CREATED_AT,
            signal_type="MISSING_TIMEOUT",
            affected_asset=asset,
            severity="MEDIUM",
            evidence=[
                EvidenceModel(
                    evidence_id=uuid4(),
                    source_system="action-proposal-test",
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
                actor_reference=ACTOR.actor_reference,
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
        session.commit()

    yield engine
    engine.dispose()


def _command(
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
) -> PrepareActionProposalCommand:
    return PrepareActionProposalCommand(technical_debt_id=technical_debt_id)


def _prepare(
    engine: Engine,
    command: PrepareActionProposalCommand | None = None,
    *,
    actor: HumanActorContext = ACTOR,
    preparation: ActionPreparationContext = PREPARATION,
    new_id: Callable[[], UUID] | None = None,
) -> ActionProposal:
    with Session(engine) as session:
        return prepare_action_proposal(
            session,
            command if command is not None else _command(),
            actor,
            preparation,
            clock=lambda: CREATED_AT,
            new_id=new_id,
        )


def _proposal_count(
    engine: Engine,
    technical_debt_id: UUID = TECHNICAL_DEBT_ID,
) -> int:
    with Session(engine) as session:
        count = session.scalar(
            select(func.count())
            .select_from(ActionProposalModel)
            .where(ActionProposalModel.technical_debt_id == technical_debt_id)
        )
        return int(count or 0)


def test_prepare_for_registered_technical_debt_succeeds(
    database_engine: Engine,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_ID)

    assert proposal.technical_debt_id == TECHNICAL_DEBT_ID
    assert proposal.action_type is ActionType.CREATE_GITHUB_ISSUE
    assert proposal.action_proposal_id == PROPOSAL_ID
    assert proposal.reconciliation_marker == action_proposal_reconciliation_marker(
        PROPOSAL_ID
    )
    assert proposal.prepared_by == ACTOR.actor_reference
    assert proposal.created_at == CREATED_AT
    assert _proposal_count(database_engine) == 1

    with Session(database_engine) as session:
        loaded = load_action_proposal(session, PROPOSAL_ID)
        assert loaded == proposal


def test_missing_technical_debt_is_typed_and_writes_nothing(
    database_engine: Engine,
) -> None:
    unknown_id = uuid4()
    with pytest.raises(TechnicalDebtNotFound, match="does not exist"):
        _prepare(database_engine, _command(unknown_id))

    assert _proposal_count(database_engine, unknown_id) == 0
    assert _proposal_count(database_engine) == 0


def test_unregistered_technical_debt_is_typed_and_writes_nothing(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Unregistered:
        lifecycle_status = "CLOSED"
        source_candidate_id = CANDIDATE_ID

    monkeypatch.setattr(
        "app.actions.preparation.load_technical_debt",
        lambda *_args, **_kwargs: _Unregistered(),
    )

    with pytest.raises(TechnicalDebtNotRegistered, match="not REGISTERED"):
        _prepare(database_engine)

    assert _proposal_count(database_engine) == 0


def test_two_prepares_for_the_same_technical_debt_both_succeed(
    database_engine: Engine,
) -> None:
    first = _prepare(database_engine, new_id=lambda: PROPOSAL_ID)
    remaining = [SECOND_PROPOSAL_ID]

    second = _prepare(database_engine, new_id=lambda: remaining.pop(0))

    assert first.action_proposal_id != second.action_proposal_id
    assert first.reconciliation_marker != second.reconciliation_marker
    assert first.technical_debt_id == second.technical_debt_id == TECHNICAL_DEBT_ID
    assert _proposal_count(database_engine) == 2


def test_target_repository_comes_from_server_owned_preparation_context(
    database_engine: Engine,
) -> None:
    context = ActionPreparationContext(
        target_repository_owner="prepared-owner",
        target_repository_name="prepared-repo",
    )

    proposal = _prepare(database_engine, preparation=context)

    assert proposal.target_repository_owner == "prepared-owner"
    assert proposal.target_repository_name == "prepared-repo"


def test_command_cannot_manufacture_title_or_body(database_engine: Engine) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_ID)

    with Session(database_engine) as session:
        technical_debt = load_technical_debt(session, TECHNICAL_DEBT_ID)
        candidate = load_candidate(session, CANDIDATE_ID)
        assert technical_debt is not None
        assert candidate is not None

    assert proposal.payload.title == compose_github_issue_title(candidate)
    assert proposal.payload.body == compose_github_issue_body(
        technical_debt=technical_debt,
        candidate=candidate,
        action_proposal_id=PROPOSAL_ID,
    )
    assert proposal.payload.title == "Technical debt: repo-borealis-renderer"
    assert "Potential missing request timeout" in proposal.payload.body


def test_prepared_by_is_server_owned_actor_reference(database_engine: Engine) -> None:
    actor = HumanActorContext(actor_reference="poc:governance-reviewer")
    proposal = _prepare(database_engine, actor=actor)

    assert proposal.prepared_by == "poc:governance-reviewer"
    assert "prepared_by" not in PrepareActionProposalCommand.__dataclass_fields__


def test_prepare_fingerprint_matches_final_body_including_marker(
    database_engine: Engine,
) -> None:
    proposal = _prepare(database_engine, new_id=lambda: PROPOSAL_ID)
    marker = action_proposal_reconciliation_marker(PROPOSAL_ID)

    assert marker in proposal.payload.body
    assert proposal.payload_fingerprint == canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner=PREPARATION.target_repository_owner,
        target_repository_name=PREPARATION.target_repository_name,
        title=proposal.payload.title,
        body=proposal.payload.body,
    )
    body_without_marker = proposal.payload.body.replace(marker, "")
    assert canonical_action_payload_fingerprint(
        action_type=ActionType.CREATE_GITHUB_ISSUE.value,
        target_repository_owner=PREPARATION.target_repository_owner,
        target_repository_name=PREPARATION.target_repository_name,
        title=proposal.payload.title,
        body=body_without_marker,
    ) != proposal.payload_fingerprint


def test_prepare_does_not_invoke_github_or_http(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("prepare must not perform HTTP or GitHub calls")

    monkeypatch.setattr("httpx.Client", forbidden)
    monkeypatch.setattr("httpx.get", forbidden)
    monkeypatch.setattr("httpx.post", forbidden)

    proposal = _prepare(database_engine)

    assert proposal.action_type is ActionType.CREATE_GITHUB_ISSUE
    assert _proposal_count(database_engine) == 1


def test_actions_package_has_no_github_or_http_imports() -> None:
    imported: set[str] = set()
    source_chunks: list[str] = []
    for path in sorted(ACTIONS_DIR.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        source_chunks.append(text)
        module = ast.parse(text, filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

    joined = "\n".join(source_chunks)
    assert not any(
        name == prefix or name.startswith(f"{prefix}.")
        for name in imported
        for prefix in (
            "httpx",
            "app.infrastructure.github_issues",
            "app.connectors.github_issues",
        )
    )
    assert "client.post(" not in joined
    assert "httpx.post" not in joined
    assert "GITHUB_TOKEN" not in joined


def test_prepare_signature_requires_server_owned_contexts() -> None:
    parameters = inspect.signature(prepare_action_proposal).parameters

    assert list(parameters)[:4] == [
        "session",
        "command",
        "actor_context",
        "preparation_context",
    ]
    assert parameters["actor_context"].default is inspect.Parameter.empty
    assert parameters["preparation_context"].default is inspect.Parameter.empty


def test_active_session_transaction_is_rejected_before_writes(
    database_engine: Engine,
) -> None:
    with Session(database_engine) as session:
        session.get(CandidateModel, CANDIDATE_ID)
        assert session.in_transaction()
        with pytest.raises(RuntimeError, match="transaction-free Session"):
            prepare_action_proposal(
                session,
                _command(),
                ACTOR,
                PREPARATION,
                clock=lambda: CREATED_AT,
            )
        assert session.in_transaction()

    assert _proposal_count(database_engine) == 0


def test_prepare_rolls_back_when_persistence_fails(
    database_engine: Engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_persist(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("forced ActionProposal persistence failure")

    monkeypatch.setattr(
        "app.actions.preparation.persist_action_proposal",
        fail_persist,
    )

    with Session(database_engine) as session:
        with pytest.raises(RuntimeError, match="forced ActionProposal"):
            prepare_action_proposal(
                session,
                _command(),
                ACTOR,
                PREPARATION,
                clock=lambda: CREATED_AT,
            )

    assert _proposal_count(database_engine) == 0


def test_reconciliation_marker_uniqueness_maps_to_persistence_conflict() -> None:
    error = IntegrityError(
        "INSERT",
        {},
        Exception(
            "Violation of UNIQUE KEY constraint "
            "'uq_action_proposals_reconciliation_marker'"
        ),
    )

    mapped = map_action_proposal_integrity_error(error)

    assert isinstance(mapped, ActionProposalPersistenceConflict)


def test_unknown_integrity_error_is_not_converted_to_action_proposal_semantics() -> (
    None
):
    error = IntegrityError("INSERT", {}, Exception("FOREIGN KEY constraint failed"))

    assert map_action_proposal_integrity_error(error) is error
