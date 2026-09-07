from dataclasses import dataclass
from uuid import UUID

from app.core.config import Settings
from app.domain.action_approvals import is_canonical_payload_fingerprint


class TechnicalDebtNotFound(ValueError):
    """The prepare command referenced a TechnicalDebt that does not exist."""


class TechnicalDebtNotRegistered(ValueError):
    """The TechnicalDebt is not in REGISTERED lifecycle status."""


class InvalidActionPreparationTarget(ValueError):
    """Target repository identity is missing or blank."""


class ActionProposalSourceContextMissing(ValueError):
    """The source Candidate required to compose the proposal is missing."""


class ActionProposalPersistenceConflict(ValueError):
    """An ActionProposal write violated a durable integrity guarantee."""


class ActionProposalNotFound(ValueError):
    """The approval command referenced an ActionProposal that does not exist."""


class ActionProposalDoesNotBelongToTechnicalDebt(ValueError):
    """The ActionProposal is not on the path TechnicalDebt."""


class StaleActionProposalFingerprint(ValueError):
    """The client fingerprint does not match the persisted ActionProposal."""


class ActionProposalAlreadyApproved(ValueError):
    """The ActionProposal already holds an L4 approval."""


class CompetingActionApprovalExists(ValueError):
    """Another proposal already occupies the logical CREATE_GITHUB_ISSUE slot."""


class ActionApprovalPersistenceConflict(ValueError):
    """An ActionApproval write violated a durable integrity guarantee."""


class LogicalActionExecutionConflict(ValueError):
    """Another proposal occupies the logical external CREATE action."""


class ActionExecutionNotFound(ValueError):
    """The verification command referenced an ActionExecution that does not exist."""


class ActionExecutionDoesNotBelongToProposal(ValueError):
    """The ActionExecution is not on the path ActionProposal."""


class ActionExecutionNotVerifiable(ValueError):
    """The ActionExecution is in a definite state that is not read-back eligible."""


class ActionExecutionReconciliationUnresolved(ValueError):
    """Marker search did not prove exactly one external issue."""


class ActionVerificationUnavailable(ValueError):
    """The verification plane is disabled or cannot target the persisted repository."""


@dataclass(frozen=True)
class PrepareActionProposalCommand:
    """Untrusted prepare intent. Preview semantics are not client-supplied."""

    technical_debt_id: UUID


@dataclass(frozen=True)
class ApproveActionProposalCommand:
    """Untrusted L4 approval intent. Actor identity is not client-supplied."""

    technical_debt_id: UUID
    action_proposal_id: UUID
    expected_payload_fingerprint: str

    def __post_init__(self) -> None:
        if not is_canonical_payload_fingerprint(self.expected_payload_fingerprint):
            raise ValueError(
                "expected_payload_fingerprint must be a SHA-256 hex digest"
            )


@dataclass(frozen=True)
class ExecuteActionProposalCommand:
    """Untrusted execute intent containing identities only."""

    technical_debt_id: UUID
    action_proposal_id: UUID


@dataclass(frozen=True)
class VerifyActionExecutionCommand:
    """Untrusted verify intent containing identities only."""

    technical_debt_id: UUID
    action_proposal_id: UUID
    action_execution_id: UUID


@dataclass(frozen=True)
class ActionPreparationContext:
    """Server-owned Day 5 demo target identity. Not write authorization."""

    target_repository_owner: str
    target_repository_name: str

    def __post_init__(self) -> None:
        owner = self.target_repository_owner.strip()
        name = self.target_repository_name.strip()
        if not owner or not name:
            raise InvalidActionPreparationTarget(
                "GitHub issue target repository owner and name must be configured"
            )
        object.__setattr__(self, "target_repository_owner", owner)
        object.__setattr__(self, "target_repository_name", name)


def action_preparation_context_from_settings(
    app_settings: Settings,
) -> ActionPreparationContext:
    """Build preparation context from trusted settings, failing closed.

    This is only the bounded Day 5 demo target identity. It is not enterprise
    authorization, write permission, or the GitHub READ connector repository.
    """
    owner = (app_settings.github_issue_target_repository_owner or "").strip()
    name = (app_settings.github_issue_target_repository_name or "").strip()
    if not owner or not name:
        raise InvalidActionPreparationTarget(
            "GITHUB_ISSUE_TARGET_REPOSITORY_OWNER and "
            "GITHUB_ISSUE_TARGET_REPOSITORY_NAME must be configured"
        )
    return ActionPreparationContext(
        target_repository_owner=owner,
        target_repository_name=name,
    )
