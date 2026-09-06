from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.agent.provider_composition import build_candidate_investigation_provider
from app.agent.runtime_contracts import InvestigationProvider
from app.core.config import Settings, settings
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.engine import create_database_engine


class HumanGovernanceUnavailable(Exception):
    """The local PoC Human Validation seam is disabled or unconfigured."""


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


def human_actor_context_from_settings(app_settings: Settings) -> HumanActorContext:
    """Build the server-owned PoC HumanActorContext from trusted settings.

    This is a local configuration seam, not verified enterprise identity.
    Clients cannot supply or override actor_reference, role, or authorization.
    """
    if not app_settings.human_governance_enabled:
        raise HumanGovernanceUnavailable("Human Validation is not available")

    actor_reference = app_settings.human_governance_actor_reference
    if actor_reference is None:
        raise HumanGovernanceUnavailable("Human Validation is not available")

    return HumanActorContext(actor_reference=actor_reference)


def get_human_actor_context() -> HumanActorContext:
    """Provide the server-owned PoC HumanActorContext, or deny the request."""
    try:
        return human_actor_context_from_settings(settings)
    except HumanGovernanceUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Human Validation is not available",
        ) from error


def get_candidate_investigation_provider() -> InvestigationProvider:
    """Provide the server-selected Candidate investigation strategy."""
    return build_candidate_investigation_provider()
