from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionPreparationContext,
    InvalidActionPreparationTarget,
    action_preparation_context_from_settings,
)
from app.actions.github_issue_executor import GitHubIssueExecutor
from app.actions.github_issue_verifier import GitHubIssueVerifier
from app.agent.provider_composition import build_candidate_investigation_provider
from app.agent.runtime_contracts import InvestigationProvider
from app.core.config import Settings, settings
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.engine import create_database_engine
from app.infrastructure.github_issue_executor import (
    GitHubIssueExecutorConfiguration,
    HttpGitHubIssueExecutor,
)
from app.infrastructure.github_issue_verifier import (
    GitHubIssueVerifierConfiguration,
    HttpGitHubIssueVerifier,
)

ACTION_PREPARATION_UNAVAILABLE_DETAIL = (
    "Action preparation is unavailable because the server is not configured"
)
ACTION_APPROVAL_UNAVAILABLE_DETAIL = "Action approval is not available"
ACTION_VERIFICATION_UNAVAILABLE_DETAIL = "Action verification is not available"


class HumanGovernanceUnavailable(Exception):
    """The local PoC Human Validation seam is disabled or unconfigured."""


class ActionPreparationUnavailable(Exception):
    """Action preparation cannot proceed because server configuration is incomplete."""


class HumanActionExecutionUnavailable(Exception):
    """The local PoC L4 action-approval seam is disabled or unconfigured."""


def get_database_session() -> Iterator[Session]:
    """Provide a caller-scoped read session without committing."""
    engine = create_database_engine()
    try:
        with Session(engine) as session:
            yield session
    finally:
        engine.dispose()


def get_human_validation_session(
    session: Annotated[Session, Depends(get_database_session)],
) -> Session:
    """Return the request Session only when it is still transaction-free.

    apply_human_validation owns BEGIN/COMMIT/ROLLBACK and must not join an
    already-open transaction. This guard does not query the database.
    """
    if session.in_transaction():
        raise RuntimeError(
            "apply_human_validation requires a transaction-free Session; "
            "the service owns the governance transaction"
        )
    return session


def get_action_preparation_session(
    session: Annotated[Session, Depends(get_database_session)],
) -> Session:
    """Return the request Session only when it is still transaction-free.

    prepare_action_proposal owns BEGIN/COMMIT/ROLLBACK and must not join an
    already-open transaction. This guard does not query the database.
    """
    if session.in_transaction():
        raise RuntimeError(
            "prepare_action_proposal requires a transaction-free Session; "
            "the service owns the preparation transaction"
        )
    return session


def get_action_approval_session(
    session: Annotated[Session, Depends(get_database_session)],
) -> Session:
    """Return the request Session only when it is still transaction-free.

    approve_action_proposal owns BEGIN/COMMIT/ROLLBACK and must not join an
    already-open transaction. This guard does not query the database.
    """
    if session.in_transaction():
        raise RuntimeError(
            "approve_action_proposal requires a transaction-free Session; "
            "the service owns the approval transaction"
        )
    return session


def get_action_execution_session(
    session: Annotated[Session, Depends(get_database_session)],
) -> Session:
    """Return a transaction-free Session for the three-phase execution service."""
    if session.in_transaction():
        raise RuntimeError(
            "execute_action_proposal requires a transaction-free Session; "
            "the service owns all execution transactions"
        )
    return session


def get_action_verification_session(
    session: Annotated[Session, Depends(get_database_session)],
) -> Session:
    """Return a transaction-free Session for the two-phase verification service."""
    if session.in_transaction():
        raise RuntimeError(
            "verify_action_execution requires a transaction-free Session; "
            "the service owns all verification transactions"
        )
    return session


def get_github_issue_executor() -> GitHubIssueExecutor | None:
    """Build the dedicated writer only when the server owns a nonblank token."""
    token = settings.github_issue_executor_token
    if token is None or not token.get_secret_value().strip():
        return None
    return HttpGitHubIssueExecutor(
        GitHubIssueExecutorConfiguration(
            token=token,
            connect_timeout_seconds=(
                settings.github_issue_executor_connect_timeout_seconds
            ),
            request_timeout_seconds=(
                settings.github_issue_executor_request_timeout_seconds
            ),
        )
    )


def get_github_issue_verifier() -> GitHubIssueVerifier | None:
    """Build the dedicated reader using the server-owned execution-plane token."""
    token = settings.github_issue_executor_token
    if token is None or not token.get_secret_value().strip():
        return None
    return HttpGitHubIssueVerifier(
        GitHubIssueVerifierConfiguration(
            token=token,
            connect_timeout_seconds=(
                settings.github_issue_executor_connect_timeout_seconds
            ),
            request_timeout_seconds=(
                settings.github_issue_executor_request_timeout_seconds
            ),
        )
    )


def human_actor_context_from_actor_reference(
    app_settings: Settings,
) -> HumanActorContext:
    """Build opaque actor attribution from the configured actor reference.

    This reuses Human Validation actor attribution for prepared_by. It does
    not grant Human Validation, execution authority, or write permission.
    """
    actor_reference = app_settings.human_governance_actor_reference
    if actor_reference is None:
        raise ActionPreparationUnavailable(ACTION_PREPARATION_UNAVAILABLE_DETAIL)
    return HumanActorContext(actor_reference=actor_reference)


def human_actor_context_from_settings(app_settings: Settings) -> HumanActorContext:
    """Build the server-owned PoC HumanActorContext from trusted settings.

    This is a local configuration seam, not verified enterprise identity.
    Clients cannot supply or override actor_reference, role, or authorization.
    Human Validation still requires the enablement flag.
    """
    if not app_settings.human_governance_enabled:
        raise HumanGovernanceUnavailable("Human Validation is not available")

    try:
        return human_actor_context_from_actor_reference(app_settings)
    except ActionPreparationUnavailable as error:
        raise HumanGovernanceUnavailable("Human Validation is not available") from error


def get_human_actor_context() -> HumanActorContext:
    """Provide the server-owned PoC HumanActorContext, or deny the request."""
    try:
        return human_actor_context_from_settings(settings)
    except HumanGovernanceUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human Validation is not available",
        ) from error


def human_action_execution_actor_context_from_settings(
    app_settings: Settings,
) -> HumanActorContext:
    """Build opaque L4 approval actor attribution from trusted settings.

    HUMAN_GOVERNANCE_ENABLED does not enable this seam. The client cannot
    supply actor_reference. This is not GitHub write permission.
    """
    if not app_settings.human_action_execution_enabled:
        raise HumanActionExecutionUnavailable(ACTION_APPROVAL_UNAVAILABLE_DETAIL)

    try:
        return human_actor_context_from_actor_reference(app_settings)
    except ActionPreparationUnavailable as error:
        raise HumanActionExecutionUnavailable(
            ACTION_APPROVAL_UNAVAILABLE_DETAIL
        ) from error


def get_action_approval_actor_context() -> HumanActorContext:
    """Provide the server-owned L4 approval actor, or deny the request."""
    try:
        return human_action_execution_actor_context_from_settings(settings)
    except HumanActionExecutionUnavailable as error:
        if not settings.human_action_execution_enabled:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=ACTION_APPROVAL_UNAVAILABLE_DETAIL,
            ) from error
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ACTION_APPROVAL_UNAVAILABLE_DETAIL,
        ) from error


def get_action_preparation_actor_context() -> HumanActorContext:
    """Provide opaque prepared_by attribution without Human Validation enablement."""
    try:
        return human_actor_context_from_actor_reference(settings)
    except ActionPreparationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ACTION_PREPARATION_UNAVAILABLE_DETAIL,
        ) from error


def get_action_preparation_context() -> ActionPreparationContext:
    """Provide the server-owned Day 5 demo target identity, failing closed."""
    try:
        return action_preparation_context_from_settings(settings)
    except InvalidActionPreparationTarget as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ACTION_PREPARATION_UNAVAILABLE_DETAIL,
        ) from error


def get_candidate_investigation_provider() -> InvestigationProvider:
    """Provide the server-selected Candidate investigation strategy."""
    return build_candidate_investigation_provider()
