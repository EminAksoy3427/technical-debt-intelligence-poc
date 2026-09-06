import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    HumanGovernanceUnavailable,
    get_human_actor_context,
    human_actor_context_from_settings,
)
from app.core.config import Settings, settings
from app.governance.contracts import HumanActorContext


def test_settings_seam_returns_server_owned_actor() -> None:
    context = human_actor_context_from_settings(
        Settings(
            _env_file=None,
            human_governance_enabled=True,
            human_governance_actor_reference="poc:local-reviewer",
        )
    )

    assert isinstance(context, HumanActorContext)
    assert context.actor_reference == "poc:local-reviewer"


def test_settings_seam_is_unavailable_when_disabled() -> None:
    with pytest.raises(HumanGovernanceUnavailable, match="not available"):
        human_actor_context_from_settings(Settings(_env_file=None))


def test_fastapi_dependency_denies_disabled_governance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "human_governance_enabled", False)

    with pytest.raises(HTTPException) as error:
        get_human_actor_context()

    assert error.value.status_code == 403
    assert error.value.detail == "Human Validation is not available"


def test_fastapi_dependency_uses_configured_server_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "human_governance_enabled", True)
    monkeypatch.setattr(
        settings,
        "human_governance_actor_reference",
        "poc:local-reviewer",
    )

    context = get_human_actor_context()

    assert context.actor_reference == "poc:local-reviewer"
