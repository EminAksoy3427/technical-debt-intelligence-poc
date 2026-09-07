from dataclasses import dataclass
from uuid import UUID

from app.core.config import Settings


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


@dataclass(frozen=True)
class PrepareActionProposalCommand:
    """Untrusted prepare intent. Preview semantics are not client-supplied."""

    technical_debt_id: UUID


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
