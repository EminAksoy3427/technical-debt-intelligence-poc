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
