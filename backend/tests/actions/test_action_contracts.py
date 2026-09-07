from dataclasses import FrozenInstanceError
from uuid import uuid4

import pytest

from app.actions.contracts import (
    ActionPreparationContext,
    InvalidActionPreparationTarget,
    PrepareActionProposalCommand,
    action_preparation_context_from_settings,
)
from app.core.config import Settings


def test_prepare_command_only_carries_technical_debt_identity() -> None:
    technical_debt_id = uuid4()
    command = PrepareActionProposalCommand(technical_debt_id=technical_debt_id)

    fields = PrepareActionProposalCommand.__dataclass_fields__
    assert command.technical_debt_id == technical_debt_id
    assert set(fields) == {"technical_debt_id"}
    assert "action_type" not in fields
    assert "title" not in fields
    assert "body" not in fields
    assert "target_repository_owner" not in fields
    assert "target_repository_name" not in fields
    assert "prepared_by" not in fields
    assert "payload_fingerprint" not in fields
    assert "reconciliation_marker" not in fields


def test_prepare_command_is_immutable() -> None:
    command = PrepareActionProposalCommand(technical_debt_id=uuid4())

    with pytest.raises(FrozenInstanceError):
        command.technical_debt_id = uuid4()  # type: ignore[misc]


def test_preparation_context_is_server_owned_and_immutable() -> None:
    context = ActionPreparationContext(
        target_repository_owner="tdi-demo-target",
        target_repository_name="tdi-action-preview",
    )

    assert context.target_repository_owner == "tdi-demo-target"
    assert context.target_repository_name == "tdi-action-preview"
    with pytest.raises(FrozenInstanceError):
        context.target_repository_owner = "other"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("owner", "name"),
    [(None, "repo"), ("owner", None), ("", "repo"), ("owner", "  "), (None, None)],
)
def test_settings_fail_closed_when_preparation_target_is_missing(
    owner: str | None,
    name: str | None,
) -> None:
    app_settings = Settings(
        _env_file=None,
        github_issue_target_repository_owner=owner,
        github_issue_target_repository_name=name,
    )

    with pytest.raises(InvalidActionPreparationTarget, match="must be configured"):
        action_preparation_context_from_settings(app_settings)


def test_preparation_context_factory_uses_dedicated_target_settings() -> None:
    app_settings = Settings(
        _env_file=None,
        github_repository_owner="EminAksoy3427",
        github_repository_name="technical-debt-connector-demo",
        github_issue_target_repository_owner="tdi-demo-target",
        github_issue_target_repository_name="tdi-action-preview",
    )

    context = action_preparation_context_from_settings(app_settings)

    assert context.target_repository_owner == "tdi-demo-target"
    assert context.target_repository_name == "tdi-action-preview"
    assert context.target_repository_owner != app_settings.github_repository_owner
    assert context.target_repository_name != app_settings.github_repository_name
