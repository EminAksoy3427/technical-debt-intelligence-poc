from enum import StrEnum

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentProviderName(StrEnum):
    DETERMINISTIC = "deterministic"
    OPENAI = "openai"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_title: str = "Technical Debt Intelligence & Governance PoC"
    api_v1_prefix: str = "/api/v1"
    database_url: SecretStr | None = None
    database_connection_timeout_seconds: int = Field(default=5, gt=0)
    github_repository_owner: str | None = None
    github_repository_name: str | None = None
    github_request_timeout_seconds: int = Field(default=5, gt=0)
    github_issue_target_repository_owner: str | None = None
    github_issue_target_repository_name: str | None = None
    agent_max_iterations: int = Field(default=6, gt=0)
    agent_max_tool_calls: int = Field(default=3, gt=0)
    agent_run_timeout_seconds: int = Field(default=60, gt=0)
    agent_tool_timeout_seconds: int = Field(default=5, gt=0)
    agent_provider: AgentProviderName = AgentProviderName.DETERMINISTIC
    openai_api_key: SecretStr | None = None
    openai_model: str | None = None
    openai_request_timeout_seconds: int = Field(default=30, gt=0)
    cors_allowed_origins: list[str] = Field(default_factory=list)
    allow_development_data_population: bool = False
    human_governance_enabled: bool = False
    human_governance_actor_reference: str | None = None
    human_action_execution_enabled: bool = False

    @field_validator("cors_allowed_origins")
    @classmethod
    def cors_allowed_origins_must_be_explicit(cls, origins: list[str]) -> list[str]:
        normalized: list[str] = []
        for origin in origins:
            value = origin.strip()
            if not value:
                raise ValueError("CORS allowed origins must not be blank")
            if value == "*":
                raise ValueError("CORS allowed origins must not use a wildcard")
            normalized.append(value)
        return normalized

    @field_validator("openai_model")
    @classmethod
    def normalize_openai_model(cls, model: str | None) -> str | None:
        if model is None:
            return None
        normalized = model.strip()
        return normalized or None

    @field_validator("human_governance_actor_reference")
    @classmethod
    def normalize_human_governance_actor_reference(
        cls,
        actor_reference: str | None,
    ) -> str | None:
        if actor_reference is None:
            return None
        normalized = actor_reference.strip()
        return normalized or None

    @field_validator(
        "github_issue_target_repository_owner",
        "github_issue_target_repository_name",
    )
    @classmethod
    def normalize_github_issue_target_repository_identity(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @model_validator(mode="after")
    def require_human_governance_actor_reference(self) -> "Settings":
        if not self.human_governance_enabled:
            return self
        if self.human_governance_actor_reference is None:
            raise ValueError(
                "HUMAN_GOVERNANCE_ACTOR_REFERENCE is required when "
                "HUMAN_GOVERNANCE_ENABLED=true"
            )
        return self

    @model_validator(mode="after")
    def require_actor_when_action_execution_enabled(self) -> "Settings":
        if not self.human_action_execution_enabled:
            return self
        if self.human_governance_actor_reference is None:
            raise ValueError(
                "HUMAN_GOVERNANCE_ACTOR_REFERENCE is required when "
                "HUMAN_ACTION_EXECUTION_ENABLED=true"
            )
        return self

    @model_validator(mode="after")
    def require_live_provider_configuration(self) -> "Settings":
        if self.agent_provider is not AgentProviderName.OPENAI:
            return self

        has_api_key = (
            self.openai_api_key is not None
            and bool(self.openai_api_key.get_secret_value().strip())
        )
        if not has_api_key or self.openai_model is None:
            raise ValueError(
                "OPENAI_API_KEY and OPENAI_MODEL are required when "
                "AGENT_PROVIDER=openai"
            )
        return self


settings = Settings()
