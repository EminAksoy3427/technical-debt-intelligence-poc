import sys
from types import SimpleNamespace

from pydantic import SecretStr

from app.agent.deterministic_provider import (
    DeterministicCandidateInvestigationProvider,
)
from app.agent.openai_provider import OpenAIProvider
from app.agent.provider_composition import (
    build_candidate_investigation_provider,
    create_openai_client,
)
from app.core.config import Settings


class FakeClient:
    def __init__(self) -> None:
        self.responses = SimpleNamespace()


def test_deterministic_provider_is_the_default_and_does_not_create_client() -> None:
    factory_called = False

    def client_factory(**_kwargs: object) -> FakeClient:
        nonlocal factory_called
        factory_called = True
        return FakeClient()

    provider = build_candidate_investigation_provider(
        Settings(_env_file=None, agent_provider="deterministic"),
        openai_client_factory=client_factory,
    )

    assert isinstance(provider, DeterministicCandidateInvestigationProvider)
    assert factory_called is False


def test_openai_provider_is_selected_from_server_settings() -> None:
    secret = "test-openai-secret-sentinel"
    received: dict[str, object] = {}

    def client_factory(**kwargs: object) -> FakeClient:
        received.update(kwargs)
        return FakeClient()

    provider = build_candidate_investigation_provider(
        Settings(
            _env_file=None,
            agent_provider="openai",
            openai_api_key=secret,
            openai_model="test-model",
            openai_request_timeout_seconds=45,
            agent_run_timeout_seconds=20,
        ),
        openai_client_factory=client_factory,
    )

    assert isinstance(provider, OpenAIProvider)
    assert received["request_timeout_seconds"] == 20
    assert isinstance(received["api_key"], SecretStr)
    assert secret not in repr(provider)
    assert secret not in repr(received["api_key"])


def test_official_client_disables_sdk_retries_and_sets_http_timeout(
    monkeypatch,
) -> None:
    received: dict[str, object] = {}

    class FakeOpenAI:
        def __init__(self, **kwargs: object) -> None:
            received.update(kwargs)
            self.responses = SimpleNamespace()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))

    create_openai_client(
        api_key=SecretStr("test-openai-secret-sentinel"),
        request_timeout_seconds=12,
    )

    assert received == {
        "api_key": "test-openai-secret-sentinel",
        "timeout": 12,
        "max_retries": 0,
    }
