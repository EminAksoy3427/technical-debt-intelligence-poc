from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.action_proposals import (
    ActionProposal,
    ActionType,
    GitHubIssuePayload,
)
from app.infrastructure.database.action_proposal_models import ActionProposalModel


def persist_action_proposal(session: Session, proposal: ActionProposal) -> None:
    """Insert one ActionProposal in the caller-owned transaction."""
    session.add(
        ActionProposalModel(
            action_proposal_id=proposal.action_proposal_id,
            technical_debt_id=proposal.technical_debt_id,
            action_type=proposal.action_type.value,
            target_repository_owner=proposal.target_repository_owner,
            target_repository_name=proposal.target_repository_name,
            title=proposal.payload.title,
            body=proposal.payload.body,
            payload_fingerprint=proposal.payload_fingerprint,
            reconciliation_marker=proposal.reconciliation_marker,
            prepared_by=proposal.prepared_by,
            created_at=proposal.created_at,
        )
    )
    session.flush()


def load_action_proposal(
    session: Session,
    action_proposal_id: UUID,
) -> ActionProposal | None:
    persisted = session.get(ActionProposalModel, action_proposal_id)
    if persisted is None:
        return None
    return _action_proposal_contract(persisted)


def list_action_proposals_for_technical_debt(
    session: Session,
    technical_debt_id: UUID,
) -> tuple[ActionProposal, ...]:
    """Load ActionProposals for one TechnicalDebt, oldest then newest."""
    persisted = session.scalars(
        select(ActionProposalModel)
        .where(ActionProposalModel.technical_debt_id == technical_debt_id)
        .order_by(
            ActionProposalModel.created_at.asc(),
            ActionProposalModel.action_proposal_id.asc(),
        )
    ).all()
    return tuple(_action_proposal_contract(item) for item in persisted)


def _action_proposal_contract(persisted: ActionProposalModel) -> ActionProposal:
    return ActionProposal(
        action_proposal_id=persisted.action_proposal_id,
        technical_debt_id=persisted.technical_debt_id,
        action_type=ActionType(persisted.action_type),
        target_repository_owner=persisted.target_repository_owner,
        target_repository_name=persisted.target_repository_name,
        payload=GitHubIssuePayload(
            title=persisted.title,
            body=persisted.body,
        ),
        payload_fingerprint=persisted.payload_fingerprint,
        reconciliation_marker=persisted.reconciliation_marker,
        prepared_by=persisted.prepared_by,
        created_at=_as_timezone_aware(persisted.created_at),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
