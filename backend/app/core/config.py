from pydantic import Field, SecretStr
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


settings = Settings()
