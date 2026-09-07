import pytest
from fastapi import HTTPException

from app.api.dependencies import (
    ACTION_APPROVAL_UNAVAILABLE_DETAIL,
    ACTION_PREPARATION_UNAVAILABLE_DETAIL,
    ActionPreparationUnavailable,
    HumanActionExecutionUnavailable,
    HumanGovernanceUnavailable,
    get_action_approval_actor_context,
    get_action_preparation_actor_context,
    get_action_preparation_context,
    get_human_actor_context,
    human_action_execution_actor_context_from_settings,
    human_actor_context_from_actor_reference,
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


def test_action_preparation_reuses_actor_without_human_validation_enablement() -> None:
    context = human_actor_context_from_actor_reference(
        Settings(
            _env_file=None,
            human_governance_enabled=False,
            human_governance_actor_reference="poc:local-reviewer",
        )
    )

    assert context.actor_reference == "poc:local-reviewer"
    with pytest.raises(HumanGovernanceUnavailable, match="not available"):
        human_actor_context_from_settings(
            Settings(
                _env_file=None,
                human_governance_enabled=False,
                human_governance_actor_reference="poc:local-reviewer",
            )
        )


def test_action_preparation_actor_fails_closed_when_unconfigured() -> None:
    with pytest.raises(ActionPreparationUnavailable, match="not configured"):
        human_actor_context_from_actor_reference(Settings(_env_file=None))


def test_action_preparation_actor_dependency_uses_configured_actor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "human_governance_enabled", False)
    monkeypatch.setattr(
        settings,
        "human_governance_actor_reference",
        "poc:local-reviewer",
    )

    context = get_action_preparation_actor_context()

    assert context.actor_reference == "poc:local-reviewer"


def test_action_preparation_context_dependency_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "github_issue_target_repository_owner", None)
    monkeypatch.setattr(settings, "github_issue_target_repository_name", None)

    with pytest.raises(HTTPException) as error:
        get_action_preparation_context()

    assert error.value.status_code == 503
    assert error.value.detail == ACTION_PREPARATION_UNAVAILABLE_DETAIL
    assert "GITHUB_ISSUE_TARGET" not in str(error.value.detail)


def test_action_approval_requires_execution_flag_not_human_validation() -> None:
    context = human_action_execution_actor_context_from_settings(
        Settings(
            _env_file=None,
            human_governance_enabled=False,
            human_action_execution_enabled=True,
            human_governance_actor_reference="poc:local-reviewer",
        )
    )

    assert context.actor_reference == "poc:local-reviewer"
    with pytest.raises(HumanActionExecutionUnavailable, match="not available"):
        human_action_execution_actor_context_from_settings(
            Settings(
                _env_file=None,
                human_governance_enabled=True,
                human_action_execution_enabled=False,
                human_governance_actor_reference="poc:local-reviewer",
            )
        )


def test_action_approval_dependency_denies_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "human_action_execution_enabled", False)
    monkeypatch.setattr(
        settings,
        "human_governance_actor_reference",
        "poc:local-reviewer",
    )

    with pytest.raises(HTTPException) as error:
        get_action_approval_actor_context()

    assert error.value.status_code == 403
    assert error.value.detail == ACTION_APPROVAL_UNAVAILABLE_DETAIL


def test_action_approval_dependency_fails_closed_when_actor_cleared_at_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Runtime mutation only. Invalid env config fails in Settings, not here."""
    monkeypatch.setattr(settings, "human_action_execution_enabled", True)
    monkeypatch.setattr(settings, "human_governance_actor_reference", None)

    with pytest.raises(HTTPException) as error:
        get_action_approval_actor_context()

    assert error.value.status_code == 503
    assert error.value.detail == ACTION_APPROVAL_UNAVAILABLE_DETAIL
    assert "HUMAN_" not in str(error.value.detail)
    assert error.value.detail != ACTION_PREPARATION_UNAVAILABLE_DETAIL
