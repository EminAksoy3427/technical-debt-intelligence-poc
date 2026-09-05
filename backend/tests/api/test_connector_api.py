from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.connectors.contracts import ConnectorRegistration
from app.connectors.registry import list_connectors as real_list_connectors
from app.main import app

API_PATH = "/api/v1/connectors"
DEPENDENCY_LIFECYCLE_SOURCE = (
    Path(__file__).resolve().parents[3]
    / "synthetic_sources"
    / "dependency_lifecycle_findings.json"
)

client = TestClient(app)

DEPENDENCY_LIFECYCLE_ITEM = {
    "connector_id": "dependency-lifecycle",
    "display_name": "Dependency Lifecycle",
    "version": "1.0.0",
    "source_system": "dependency-lifecycle",
    "transport": "local-json",
    "read_only": True,
    "status": "registered",
}

GITHUB_ISSUES_ITEM = {
    "connector_id": "github-issues",
    "display_name": "GitHub Issues",
    "version": "1.0.0",
    "source_system": "github-issues",
    "transport": "https",
    "read_only": True,
    "status": "registered",
}

FORBIDDEN_SUBSTRINGS = (
    "healthy",
    "operational",
    "online",
    "connected",
    "available",
    "last_run",
    "last_success",
    "last_error",
    "last_attempt",
    "checkpoint",
    "cursor",
    "enabled",
    "github_repository_owner",
    "github_repository_name",
    "github_request_timeout_seconds",
    "acquire",
    "authorization",
    "github_token",
    "gh_token",
    "synthetic_sources",
    "dependency_lifecycle_findings.json",
    "issue title",
    "html_url",
    "source payload",
)


def test_connector_list_returns_registered_registry_descriptors() -> None:
    response = client.get(API_PATH)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "items": [DEPENDENCY_LIFECYCLE_ITEM, GITHUB_ISSUES_ITEM],
        "count": 2,
    }
    assert [item["connector_id"] for item in body["items"]] == [
        "dependency-lifecycle",
        "github-issues",
    ]


def test_connector_list_does_not_expose_speculative_or_secret_fields() -> None:
    response = client.get(API_PATH)

    assert response.status_code == 200
    serialized = str(response.json()).lower()
    for forbidden in FORBIDDEN_SUBSTRINGS:
        assert forbidden not in serialized
    for item in response.json()["items"]:
        assert set(item) == {
            "connector_id",
            "display_name",
            "version",
            "source_system",
            "transport",
            "read_only",
            "status",
        }
        assert item["status"] == "registered"


def test_connector_list_does_not_call_acquisition_callables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    acquire_calls: list[str] = []
    wrapped: list[ConnectorRegistration[object, object]] = []
    for registration in real_list_connectors():
        connector_id = registration.descriptor.connector_id
        original_acquire = registration.acquire

        def tracked_acquire(
            configuration: object,
            *,
            _connector_id: str = connector_id,
            _original=original_acquire,
        ) -> object:
            acquire_calls.append(_connector_id)
            return _original(configuration)

        wrapped.append(
            ConnectorRegistration(
                descriptor=registration.descriptor,
                acquire=tracked_acquire,
            )
        )

    monkeypatch.setattr(
        "app.api.v1.connectors.list_connectors",
        lambda: tuple(wrapped),
    )

    response = client.get(API_PATH)

    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert acquire_calls == []


def test_connector_list_does_not_touch_github_source_file_or_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    github_client_constructions: list[tuple[tuple[object, ...], dict[str, object]]] = []
    github_fetches: list[object] = []
    source_reads: list[Path] = []
    engine_calls: list[tuple[tuple[object, ...], dict[str, object]]] = []
    original_read_text = Path.read_text

    class ForbiddenGitHubClient:
        def __init__(self, *args: object, **kwargs: object) -> None:
            github_client_constructions.append((args, kwargs))
            raise AssertionError("GitHub HTTP client must not be constructed")

    def forbidden_fetch(configuration: object) -> tuple[object, ...]:
        github_fetches.append(configuration)
        raise AssertionError("GitHub Issues must not be fetched")

    def guarded_read_text(self: Path, *args: object, **kwargs: object) -> str:
        resolved = self.resolve()
        if (
            resolved == DEPENDENCY_LIFECYCLE_SOURCE.resolve()
            or self.name == "dependency_lifecycle_findings.json"
        ):
            source_reads.append(self)
            raise AssertionError("Dependency-lifecycle source file must not be read")
        return original_read_text(self, *args, **kwargs)

    def forbidden_engine(*args: object, **kwargs: object) -> object:
        engine_calls.append((args, kwargs))
        raise AssertionError("Connector list must not create a database engine")

    monkeypatch.setattr(
        "app.infrastructure.github_issues.httpx.Client",
        ForbiddenGitHubClient,
    )
    monkeypatch.setattr(
        "app.connectors.github_issues.fetch_github_issue_records",
        forbidden_fetch,
    )
    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(
        "app.api.dependencies.create_database_engine",
        forbidden_engine,
    )
    monkeypatch.setattr(
        "app.infrastructure.database.engine.create_database_engine",
        forbidden_engine,
    )

    response = client.get(API_PATH)

    assert response.status_code == 200
    assert response.json() == {
        "items": [DEPENDENCY_LIFECYCLE_ITEM, GITHUB_ISSUES_ITEM],
        "count": 2,
    }
    assert github_client_constructions == []
    assert github_fetches == []
    assert source_reads == []
    assert engine_calls == []


def test_empty_connector_registry_returns_deterministic_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("app.api.v1.connectors.list_connectors", lambda: ())

    response = client.get(API_PATH)

    assert response.status_code == 200
    assert response.json() == {"items": [], "count": 0}


def test_connector_list_has_no_mutating_routes() -> None:
    assert client.post(API_PATH).status_code == 405
    assert client.put(API_PATH).status_code == 405
    assert client.patch(API_PATH).status_code == 405
    assert client.delete(API_PATH).status_code == 405
    assert client.get(f"{API_PATH}/github-issues").status_code == 404
