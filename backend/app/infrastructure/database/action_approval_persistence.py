from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.domain.action_approvals import ActionApproval
from app.domain.action_proposals import ActionType
from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_proposal_models import ActionProposalModel
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel

_MSSQL_TECHNICAL_DEBT_ACTION_APPROVAL_LOCK = "WITH (UPDLOCK, HOLDLOCK)"


def technical_debt_action_approval_boundary_statement(
    technical_debt_id: UUID,
) -> Select[tuple[TechnicalDebtModel]]:
    """Select one TechnicalDebt with MSSQL UPDLOCK, HOLDLOCK on that dialect only."""
    return (
        select(TechnicalDebtModel)
        .where(TechnicalDebtModel.technical_debt_id == technical_debt_id)
        .with_hint(
            TechnicalDebtModel,
            _MSSQL_TECHNICAL_DEBT_ACTION_APPROVAL_LOCK,
            dialect_name="mssql",
        )
    )


def lock_technical_debt_for_action_approval(
    session: Session,
    technical_debt_id: UUID,
) -> TechnicalDebtModel | None:
    """Load the TechnicalDebt row that serializes L4 approval for that identity."""
    return session.scalar(
        technical_debt_action_approval_boundary_statement(technical_debt_id)
    )


def persist_action_approval(session: Session, approval: ActionApproval) -> None:
    """Insert one append-only ActionApproval in the caller-owned transaction."""
    session.add(
        ActionApprovalModel(
            action_approval_id=approval.action_approval_id,
            action_proposal_id=approval.action_proposal_id,
            payload_fingerprint=approval.payload_fingerprint,
            actor_reference=approval.actor_reference,
            created_at=approval.created_at,
        )
    )
    session.flush()


def load_action_approval(
    session: Session,
    action_approval_id: UUID,
) -> ActionApproval | None:
    persisted = session.get(ActionApprovalModel, action_approval_id)
    if persisted is None:
        return None
    return _action_approval_contract(persisted)


def load_action_approval_for_proposal(
    session: Session,
    action_proposal_id: UUID,
) -> ActionApproval | None:
    persisted = session.scalar(
        select(ActionApprovalModel).where(
            ActionApprovalModel.action_proposal_id == action_proposal_id
        )
    )
    if persisted is None:
        return None
    return _action_approval_contract(persisted)


def list_action_approvals_for_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> tuple[ActionApproval, ...]:
    """Load ActionApprovals for one TechnicalDebt, oldest then newest."""
    persisted = session.scalars(
        select(ActionApprovalModel)
        .join(
            ActionProposalModel,
            ActionApprovalModel.action_proposal_id
            == ActionProposalModel.action_proposal_id,
        )
        .where(ActionProposalModel.technical_debt_id == technical_debt_id)
        .order_by(
            ActionApprovalModel.created_at.asc(),
            ActionApprovalModel.action_approval_id.asc(),
        )
    ).all()
    return tuple(_action_approval_contract(item) for item in persisted)


def list_create_github_issue_approvals_for_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> tuple[ActionApproval, ...]:
    """Load approvals occupying the CREATE_GITHUB_ISSUE logical slot."""
    persisted = session.scalars(
        select(ActionApprovalModel)
        .join(
            ActionProposalModel,
            ActionApprovalModel.action_proposal_id
            == ActionProposalModel.action_proposal_id,
        )
        .outerjoin(
            ActionExecutionModel,
            ActionExecutionModel.action_proposal_id
            == ActionApprovalModel.action_proposal_id,
        )
        .where(ActionProposalModel.technical_debt_id == technical_debt_id)
        .where(
            ActionProposalModel.action_type == ActionType.CREATE_GITHUB_ISSUE.value
        )
        .where(
            (ActionExecutionModel.action_execution_id.is_(None))
            | (ActionExecutionModel.status != "FAILED")
        )
        .order_by(
            ActionApprovalModel.created_at.asc(),
            ActionApprovalModel.action_approval_id.asc(),
        )
    ).all()
    return tuple(_action_approval_contract(item) for item in persisted)


def _action_approval_contract(persisted: ActionApprovalModel) -> ActionApproval:
    return ActionApproval(
        action_approval_id=persisted.action_approval_id,
        action_proposal_id=persisted.action_proposal_id,
        payload_fingerprint=persisted.payload_fingerprint,
        actor_reference=persisted.actor_reference,
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
