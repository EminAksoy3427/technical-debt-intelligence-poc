import json
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import httpx
import pytest

from app.connectors.contracts import SourceObservation
from app.connectors.github_issues import acquire_github_issue_observations
from app.core.config import Settings
from app.infrastructure.github_issues import (
    GITHUB_API_ORIGIN,
    GitHubIssueRecord,
    GitHubIssuesApiError,
    GitHubIssuesConfigurationError,
    GitHubIssuesReadConfiguration,
    GitHubIssuesResponseFormatError,
    GitHubIssuesTransportError,
    fetch_github_issue_records,
    github_issues_read_configuration_from_settings,
    parse_github_issues_json,
)

SECRET_BODY = "do-not-retain-issue-body"
SECRET_RESPONSE = "do-not-dump-response-body"
ISSUE_UPDATED_AT = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _configuration() -> GitHubIssuesReadConfiguration:
    return GitHubIssuesReadConfiguration(
        repository_owner="EminAksoy3427",
        repository_name="technical-debt-connector-demo",
        request_timeout_seconds=5,
    )


def _issue_payload(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": 3512345678,
        "number": 1,
        "title": "[TDI-DEMO] Catalog client request has no explicit timeout",
        "state": "open",
        "html_url": (
            "https://github.com/EminAksoy3427/technical-debt-connector-demo/issues/1"
        ),
        "updated_at": "2026-09-01T12:00:00Z",
        "body": SECRET_BODY,
        "labels": [{"name": "tdi-demo"}],
        "user": {"login": "synthetic-user"},
    }
    payload.update(overrides)
    return payload


class FakeResponse:
    def __init__(self, status_code: int, payload: object) -> None:
        self.status_code = status_code
        self.text = payload if isinstance(payload, str) else json.dumps(payload)


class FakeClient:
    def __init__(
        self,
        captured: dict[str, object],
        response: FakeResponse | BaseException,
    ) -> None:
        self._captured = captured
        self._response = response

    def __enter__(self) -> "FakeClient":
        return self

    def __exit__(self, *args: object) -> bool:
        return False

    def get(self, url: str, params: dict[str, str] | None = None) -> FakeResponse:
        methods = self._captured.setdefault("methods", [])
        assert isinstance(methods, list)
        methods.append("GET")
        self._captured["url"] = url
        self._captured["params"] = params
        if isinstance(self._response, BaseException):
            raise self._response
        return self._response

    def post(self, *args: object, **kwargs: object) -> None:
        methods = self._captured.setdefault("methods", [])
        assert isinstance(methods, list)
        methods.append("POST")
        raise AssertionError("GitHub Issues acquisition must not POST")

    def put(self, *args: object, **kwargs: object) -> None:
        methods = self._captured.setdefault("methods", [])
        assert isinstance(methods, list)
        methods.append("PUT")
        raise AssertionError("GitHub Issues acquisition must not PUT")

    def patch(self, *args: object, **kwargs: object) -> None:
        methods = self._captured.setdefault("methods", [])
        assert isinstance(methods, list)
        methods.append("PATCH")
        raise AssertionError("GitHub Issues acquisition must not PATCH")

    def delete(self, *args: object, **kwargs: object) -> None:
        methods = self._captured.setdefault("methods", [])
        assert isinstance(methods, list)
        methods.append("DELETE")
        raise AssertionError("GitHub Issues acquisition must not DELETE")


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeResponse | BaseException,
    captured: dict[str, object] | None = None,
) -> dict[str, object]:
    captured = {} if captured is None else captured

    def fake_client(*, timeout: object, headers: dict[str, str], **kwargs: object):
        captured["timeout"] = timeout
        captured["headers"] = headers
        captured["client_kwargs"] = kwargs
        return FakeClient(captured, response)

    monkeypatch.setattr(
        "app.infrastructure.github_issues.httpx.Client",
        fake_client,
    )
    return captured


def test_valid_github_issue_json_maps_to_immutable_record() -> None:
    records = parse_github_issues_json(json.dumps([_issue_payload()]))

    assert records == (
        GitHubIssueRecord(
            issue_id=3512345678,
            number=1,
            title="[TDI-DEMO] Catalog client request has no explicit timeout",
            state="open",
            html_url=(
                "https://github.com/EminAksoy3427/"
                "technical-debt-connector-demo/issues/1"
            ),
            updated_at=ISSUE_UPDATED_AT,
        ),
    )
    record = records[0]
    assert record.updated_at.tzinfo is not None
    assert record.updated_at.utcoffset() is not None
    with pytest.raises(FrozenInstanceError):
        record.title = "changed"  # type: ignore[misc]


def test_github_issue_record_does_not_retain_body_raw_json_or_labels() -> None:
    payload = _issue_payload()
    record = parse_github_issues_json(json.dumps([payload]))[0]

    assert "body" not in GitHubIssueRecord.__dataclass_fields__
    assert "labels" not in GitHubIssueRecord.__dataclass_fields__
    assert "raw" not in GitHubIssueRecord.__dataclass_fields__
    assert not hasattr(record, "body")
    assert SECRET_BODY not in repr(record)
    assert "tdi-demo" not in repr(record)
    assert json.dumps(payload) not in repr(record)


def test_pull_request_entries_are_ignored() -> None:
    payload = [
        _issue_payload(),
        _issue_payload(
            id=3512345679,
            number=3,
            title="A pull request must be ignored",
            html_url=(
                "https://github.com/EminAksoy3427/"
                "technical-debt-connector-demo/pull/3"
            ),
            pull_request={"url": "https://api.github.com/repos/example/pulls/3"},
        ),
    ]

    records = parse_github_issues_json(json.dumps(payload))

    assert tuple(record.number for record in records) == (1,)


def test_issue_id_becomes_source_record_id_not_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, FakeResponse(200, [_issue_payload()]))

    observations = acquire_github_issue_observations(_configuration())

    assert len(observations) == 1
    observation = observations[0]
    assert isinstance(observation, SourceObservation)
    assert observation.provenance.source_system == "github-issues"
    assert observation.provenance.source_record_id == "3512345678"
    assert observation.provenance.source_record_id != "1"
    assert observation.provenance.source_record_id != str(observation.record.number)
    assert observation.record.number == 1
    assert observation.record.title == (
        "[TDI-DEMO] Catalog client request has no explicit timeout"
    )
    assert observation.record.state == "open"
    assert observation.record.html_url.endswith("/issues/1")
    assert observation.observed_at == ISSUE_UPDATED_AT
    assert observation.observed_at == observation.record.updated_at
    assert observation.observed_at.tzinfo is not None


def test_configured_timeout_reaches_httpx_and_only_get_is_used(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured = _install_fake_client(monkeypatch, FakeResponse(200, []))

    records = fetch_github_issue_records(_configuration())

    assert records == ()
    assert captured["timeout"] == 5
    assert captured["methods"] == ["GET"]
    assert captured["url"] == (
        f"{GITHUB_API_ORIGIN}/repos/EminAksoy3427/"
        "technical-debt-connector-demo/issues"
    )
    assert captured["params"] == {"state": "open"}
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert "Authorization" not in headers
    assert "authorization" not in {key.lower() for key in headers}


@pytest.mark.parametrize(
    ("status_code", "match"),
    [
        (401, "401"),
        (403, "403"),
        (404, "404"),
        (429, "429"),
    ],
)
def test_http_error_status_maps_to_api_error_without_response_body(
    monkeypatch: pytest.MonkeyPatch,
    status_code: int,
    match: str,
) -> None:
    _install_fake_client(
        monkeypatch,
        FakeResponse(status_code, {"message": SECRET_RESPONSE}),
    )

    with pytest.raises(GitHubIssuesApiError, match=match) as error:
        fetch_github_issue_records(_configuration())

    assert error.value.status_code == status_code
    assert SECRET_RESPONSE not in str(error.value)


def test_timeout_maps_to_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    _install_fake_client(monkeypatch, httpx.TimeoutException("timed out"))

    with pytest.raises(GitHubIssuesTransportError, match="timed out"):
        fetch_github_issue_records(_configuration())


def test_connection_failure_maps_to_transport_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_fake_client(monkeypatch, httpx.ConnectError("dns lookup failed"))

    with pytest.raises(GitHubIssuesTransportError, match="could not connect"):
        fetch_github_issue_records(_configuration())


def test_malformed_json_fails_without_dumping_body() -> None:
    with pytest.raises(
        GitHubIssuesResponseFormatError,
        match="valid JSON",
    ) as error:
        parse_github_issues_json("{" + SECRET_RESPONSE)

    assert SECRET_RESPONSE not in str(error.value)


def test_missing_required_field_fails_safely() -> None:
    payload = _issue_payload()
    del payload["id"]

    with pytest.raises(GitHubIssuesResponseFormatError, match="id"):
        parse_github_issues_json(json.dumps([payload]))


def test_unexpected_required_field_type_fails_safely() -> None:
    with pytest.raises(GitHubIssuesResponseFormatError, match="integer"):
        parse_github_issues_json(json.dumps([_issue_payload(id="3512345678")]))


def test_malformed_timestamp_fails_safely() -> None:
    with pytest.raises(GitHubIssuesResponseFormatError, match="timestamp"):
        parse_github_issues_json(
            json.dumps([_issue_payload(updated_at="2026-09-01T12:00:00")])
        )


def test_missing_settings_fail_before_http(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GITHUB_REPOSITORY_OWNER", raising=False)
    monkeypatch.delenv("GITHUB_REPOSITORY_NAME", raising=False)

    with pytest.raises(GitHubIssuesConfigurationError, match="must be configured"):
        github_issues_read_configuration_from_settings(Settings(_env_file=None))
