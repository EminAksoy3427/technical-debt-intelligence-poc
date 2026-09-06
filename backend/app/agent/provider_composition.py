from typing import Protocol

from pydantic import SecretStr

from app.agent.deterministic_provider import (
    DeterministicCandidateInvestigationProvider,
)
from app.agent.openai_provider import OpenAIClient, OpenAIProvider
from app.agent.runtime_contracts import InvestigationProvider
from app.core.config import AgentProviderName, Settings, settings


class OpenAIClientFactory(Protocol):
    def __call__(
        self,
        *,
        api_key: SecretStr,
        request_timeout_seconds: int,
    ) -> OpenAIClient: ...


def create_openai_client(
    *,
    api_key: SecretStr,
    request_timeout_seconds: int,
) -> OpenAIClient:
    """Create the official SDK client without exposing its secret to providers."""
    from openai import OpenAI

    return OpenAI(
        api_key=api_key.get_secret_value(),
        timeout=request_timeout_seconds,
        max_retries=0,
    )


def build_candidate_investigation_provider(
    app_settings: Settings = settings,
    *,
    openai_client_factory: OpenAIClientFactory = create_openai_client,
) -> InvestigationProvider:
    """Select the investigation provider exclusively from server settings."""
    if app_settings.agent_provider is AgentProviderName.DETERMINISTIC:
        return DeterministicCandidateInvestigationProvider()

    api_key = app_settings.openai_api_key
    model = app_settings.openai_model
    if api_key is None or model is None:
        raise RuntimeError("Live provider configuration is incomplete")
    request_timeout_seconds = min(
        app_settings.openai_request_timeout_seconds,
        app_settings.agent_run_timeout_seconds,
    )
    client = openai_client_factory(
        api_key=api_key,
        request_timeout_seconds=request_timeout_seconds,
    )
    return OpenAIProvider(
        client=client,
        model=model,
        request_timeout_seconds=request_timeout_seconds,
    )
