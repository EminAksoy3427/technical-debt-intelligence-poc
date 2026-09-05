import pytest
from pydantic import ValidationError

from app.core.config import Settings


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
