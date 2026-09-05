import importlib
import inspect
from dataclasses import FrozenInstanceError

import pytest

from app.connectors.contracts import ConnectorDescriptor, SourceObservation
from app.connectors.github_issues import (
    GITHUB_ISSUES_CONNECTOR,
    GITHUB_ISSUES_CONNECTOR_DESCRIPTOR,
    acquire_github_issue_observations,
)
from app.connectors.registry import get_connector, list_connectors
from app.infrastructure.github_issues import (
    GitHubIssueRecord,
    GitHubIssuesReadConfiguration,
)
from app.signal_ingestion import NormalizedSignal


def _configuration() -> GitHubIssuesReadConfiguration:
    return GitHubIssuesReadConfiguration(
        repository_owner="EminAksoy3427",
        repository_name="technical-debt-connector-demo",
        request_timeout_seconds=5,
    )


def test_github_issues_descriptor_is_immutable_and_truthful() -> None:
    descriptor = GITHUB_ISSUES_CONNECTOR_DESCRIPTOR

    assert descriptor == ConnectorDescriptor(
        connector_id="github-issues",
        display_name="GitHub Issues",
        version="1.0.0",
        source_system="github-issues",
        transport="https",
        read_only=True,
    )
    assert descriptor.read_only is True
    with pytest.raises(FrozenInstanceError):
        descriptor.display_name = "Changed"  # type: ignore[misc]


def test_github_issues_connector_acquires_observations_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeResponse:
        status_code = 200
        text = (
            '[{"id": 3512345678, "number": 1, '
            '"title": "[TDI-DEMO] Catalog client request has no explicit timeout", '
            '"state": "open", '
            '"html_url": "https://github.com/EminAksoy3427/'
            'technical-debt-connector-demo/issues/1", '
            '"updated_at": "2026-09-01T12:00:00Z"}]'
        )

    class FakeClient:
        def __init__(
            self, *, timeout: object, headers: object, **kwargs: object
        ) -> None:
            del timeout, headers, kwargs

        def __enter__(self) -> "FakeClient":
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def get(self, url: str, params: dict[str, str] | None = None) -> FakeResponse:
            del url, params
            return FakeResponse()

    monkeypatch.setattr(
        "app.infrastructure.github_issues.httpx.Client",
        FakeClient,
    )

    observations = GITHUB_ISSUES_CONNECTOR.acquire(_configuration())

    assert observations
    assert all(isinstance(item, SourceObservation) for item in observations)
    assert all(isinstance(item.record, GitHubIssueRecord) for item in observations)
    assert all(not isinstance(item, NormalizedSignal) for item in observations)
    assert acquire_github_issue_observations is GITHUB_ISSUES_CONNECTOR.acquire


def test_registry_contains_github_issues_after_dependency_lifecycle() -> None:
    registrations = list_connectors()

    assert tuple(item.descriptor.connector_id for item in registrations) == (
        "dependency-lifecycle",
        "github-issues",
    )
    assert get_connector("github-issues") is GITHUB_ISSUES_CONNECTOR


def test_github_issues_implementation_is_get_only() -> None:
    source = inspect.getsource(
        importlib.import_module("app.infrastructure.github_issues")
    )

    assert "client.get(" in source
    assert "client.post(" not in source
    assert "client.put(" not in source
    assert "client.patch(" not in source
    assert "client.delete(" not in source
    assert "httpx.post" not in source
    assert "httpx.put" not in source
    assert "httpx.patch" not in source
    assert "httpx.delete" not in source
