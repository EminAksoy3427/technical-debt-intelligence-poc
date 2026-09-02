from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    cors_allowed_origins: list[str] = Field(default_factory=list)
    allow_development_data_population: bool = False

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


settings = Settings()
