import pytest
from pydantic import SecretStr, ValidationError

from app.core.config import AgentProviderName, Settings


def test_cors_allowed_origins_default_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CORS_ALLOWED_ORIGINS", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.cors_allowed_origins == []


def test_cors_allowed_origins_parse_json_list_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["http://localhost:3000"]',
    )

    app_settings = Settings(_env_file=None)

    assert app_settings.cors_allowed_origins == ["http://localhost:3000"]


def test_cors_allowed_origins_reject_wildcard() -> None:
    with pytest.raises(ValidationError, match="wildcard"):
        Settings(_env_file=None, cors_allowed_origins=["*"])


def test_cors_allowed_origins_reject_blank_origin() -> None:
    with pytest.raises(ValidationError, match="blank"):
        Settings(_env_file=None, cors_allowed_origins=[" "])


def test_development_data_population_guard_defaults_to_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ALLOW_DEVELOPMENT_DATA_POPULATION", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.allow_development_data_population is False


def test_development_data_population_guard_can_be_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ALLOW_DEVELOPMENT_DATA_POPULATION", "true")

    app_settings = Settings(_env_file=None)

    assert app_settings.allow_development_data_population is True


def test_github_request_timeout_defaults_to_five_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_REQUEST_TIMEOUT_SECONDS", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.github_request_timeout_seconds == 5


@pytest.mark.parametrize("timeout", [0, -1])
def test_github_request_timeout_must_be_greater_than_zero(timeout: int) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, github_request_timeout_seconds=timeout)


def test_github_repository_identity_loads_from_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "EminAksoy3427")
    monkeypatch.setenv("GITHUB_REPOSITORY_NAME", "technical-debt-connector-demo")

    app_settings = Settings(_env_file=None)

    assert app_settings.github_repository_owner == "EminAksoy3427"
    assert app_settings.github_repository_name == "technical-debt-connector-demo"


def test_agent_runtime_limits_have_bounded_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "AGENT_MAX_ITERATIONS",
        "AGENT_MAX_TOOL_CALLS",
        "AGENT_RUN_TIMEOUT_SECONDS",
        "AGENT_TOOL_TIMEOUT_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.agent_max_iterations == 6
    assert app_settings.agent_max_tool_calls == 3
    assert app_settings.agent_run_timeout_seconds == 60
    assert app_settings.agent_tool_timeout_seconds == 5
    assert app_settings.agent_provider is AgentProviderName.DETERMINISTIC

    field_names = set(Settings.model_fields)
    assert {
        "agent_allowed_effects",
        "agent_maximum_risk",
        "agent_granted_scopes",
        "agent_approval",
    }.isdisjoint(field_names)


@pytest.mark.parametrize(
    "field_name",
    (
        "agent_max_iterations",
        "agent_max_tool_calls",
        "agent_run_timeout_seconds",
        "agent_tool_timeout_seconds",
    ),
)
def test_agent_runtime_limits_must_be_positive(field_name: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: 0})


def test_github_issue_target_settings_are_not_write_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GITHUB_REPOSITORY_OWNER", "EminAksoy3427")
    monkeypatch.setenv("GITHUB_REPOSITORY_NAME", "technical-debt-connector-demo")
    monkeypatch.setenv("GITHUB_ISSUE_TARGET_REPOSITORY_OWNER", "tdi-demo-target")
    monkeypatch.setenv("GITHUB_ISSUE_TARGET_REPOSITORY_NAME", "tdi-action-preview")

    app_settings = Settings(_env_file=None)
    field_names = {name.lower() for name in Settings.model_fields}

    assert app_settings.github_issue_target_repository_owner == "tdi-demo-target"
    assert app_settings.github_issue_target_repository_name == "tdi-action-preview"
    assert (
        app_settings.github_issue_target_repository_owner
        != app_settings.github_repository_owner
    )
    assert (
        app_settings.github_issue_target_repository_name
        != app_settings.github_repository_name
    )
    assert "github_token" not in field_names
    assert "github_write_token" not in field_names
    assert "github_issue_token" not in field_names
    assert app_settings.human_action_execution_enabled is False
    owner_annotation = Settings.model_fields[
        "github_issue_target_repository_owner"
    ].annotation
    name_annotation = Settings.model_fields[
        "github_issue_target_repository_name"
    ].annotation
    assert owner_annotation == (str | None)
    assert name_annotation == (str | None)


def test_github_issue_target_settings_default_to_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_ISSUE_TARGET_REPOSITORY_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_ISSUE_TARGET_REPOSITORY_NAME", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.github_issue_target_repository_owner is None
    assert app_settings.github_issue_target_repository_name is None


def test_github_settings_have_no_token_and_safe_repr(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY_NAME", raising=False)

    app_settings = Settings(_env_file=None)
    field_names = {name.lower() for name in Settings.model_fields}

    assert app_settings.github_repository_owner is None
    assert app_settings.github_repository_name is None
    assert "github_token" not in field_names
    assert "gh_token" not in field_names
    rendered = repr(app_settings).lower()
    assert "github_token" not in rendered
    assert "authorization" not in rendered
    assert "gho_" not in rendered
    assert "ghp_" not in rendered


def test_github_issue_executor_token_is_optional_secret_and_repr_safe() -> None:
    secret = "test-github-executor-secret"

    app_settings = Settings(
        _env_file=None,
        github_issue_executor_token=secret,
    )

    assert isinstance(app_settings.github_issue_executor_token, SecretStr)
    assert secret not in repr(app_settings)
    assert "**********" in repr(app_settings)


@pytest.mark.parametrize(
    "field_name",
    (
        "github_issue_executor_connect_timeout_seconds",
        "github_issue_executor_request_timeout_seconds",
    ),
)
@pytest.mark.parametrize("value", (0, 121))
def test_github_issue_executor_timeouts_are_positive_and_bounded(
    field_name: str,
    value: int,
) -> None:
    if field_name.endswith("connect_timeout_seconds") and value == 121:
        value = 61
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field_name: value})


def test_deterministic_provider_requires_no_openai_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in ("AGENT_PROVIDER", "OPENAI_API_KEY", "OPENAI_MODEL"):
        monkeypatch.delenv(name, raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.agent_provider is AgentProviderName.DETERMINISTIC
    assert app_settings.openai_api_key is None
    assert app_settings.openai_model is None


@pytest.mark.parametrize(
    ("api_key", "model"),
    [(None, "test-model"), ("test-secret", None), ("", "test-model")],
)
def test_openai_provider_requires_key_and_model(
    api_key: str | None,
    model: str | None,
) -> None:
    with pytest.raises(ValidationError, match="OPENAI_API_KEY and OPENAI_MODEL"):
        Settings(
            _env_file=None,
            agent_provider="openai",
            openai_api_key=api_key,
            openai_model=model,
        )


def test_human_governance_is_disabled_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HUMAN_GOVERNANCE_ENABLED", raising=False)
    monkeypatch.delenv("HUMAN_GOVERNANCE_ACTOR_REFERENCE", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.human_governance_enabled is False
    assert app_settings.human_governance_actor_reference is None


def test_human_governance_can_be_enabled_with_server_actor_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HUMAN_GOVERNANCE_ENABLED", "true")
    monkeypatch.setenv("HUMAN_GOVERNANCE_ACTOR_REFERENCE", "poc:local-reviewer")

    app_settings = Settings(_env_file=None)

    assert app_settings.human_governance_enabled is True
    assert app_settings.human_governance_actor_reference == "poc:local-reviewer"


@pytest.mark.parametrize("actor_reference", [None, "", "   "])
def test_enabled_human_governance_requires_nonblank_actor_reference(
    actor_reference: str | None,
) -> None:
    with pytest.raises(ValidationError, match="HUMAN_GOVERNANCE_ACTOR_REFERENCE"):
        Settings(
            _env_file=None,
            human_governance_enabled=True,
            human_governance_actor_reference=actor_reference,
        )


def test_human_action_execution_is_disabled_by_default_and_independent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("HUMAN_ACTION_EXECUTION_ENABLED", raising=False)
    monkeypatch.delenv("HUMAN_GOVERNANCE_ENABLED", raising=False)

    app_settings = Settings(_env_file=None)

    assert app_settings.human_action_execution_enabled is False
    assert app_settings.human_governance_enabled is False


def test_human_action_execution_can_be_enabled_without_human_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("HUMAN_ACTION_EXECUTION_ENABLED", "true")
    monkeypatch.setenv("HUMAN_GOVERNANCE_ENABLED", "false")
    monkeypatch.setenv("HUMAN_GOVERNANCE_ACTOR_REFERENCE", "poc:local-reviewer")

    app_settings = Settings(_env_file=None)

    assert app_settings.human_action_execution_enabled is True
    assert app_settings.human_governance_enabled is False


def test_enabled_action_execution_requires_nonblank_actor_reference() -> None:
    """Invalid startup config fails in Settings and never reaches the endpoint."""
    with pytest.raises(ValidationError, match="HUMAN_ACTION_EXECUTION_ENABLED"):
        Settings(
            _env_file=None,
            human_action_execution_enabled=True,
            human_governance_actor_reference=None,
        )


def test_human_governance_actor_reference_is_not_a_secret() -> None:
    field_names = set(Settings.model_fields)
    actor_annotation = Settings.model_fields[
        "human_governance_actor_reference"
    ].annotation

    assert "human_governance_enabled" in field_names
    assert "human_action_execution_enabled" in field_names
    assert actor_annotation == (str | None)


def test_openai_api_key_is_masked_in_settings_repr() -> None:
    secret = "test-openai-secret-sentinel"

    app_settings = Settings(
        _env_file=None,
        agent_provider="openai",
        openai_api_key=secret,
        openai_model="test-model",
    )

    assert secret not in repr(app_settings)
    assert "**********" in repr(app_settings)
