import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Final

import httpx

from app.core.config import Settings

GITHUB_API_ORIGIN: Final = "https://api.github.com"
GITHUB_ISSUES_USER_AGENT: Final = "technical-debt-intelligence-poc"
GITHUB_ISSUES_ACCEPT: Final = "application/vnd.github+json"


class GitHubIssuesSourceError(RuntimeError):
    """Base error for the GitHub Issues source boundary."""


class GitHubIssuesConfigurationError(GitHubIssuesSourceError):
    """Raised when required GitHub Issues acquisition settings are missing."""


class GitHubIssuesTransportError(GitHubIssuesSourceError):
    """Raised when the GitHub HTTP call times out or cannot connect."""


class GitHubIssuesApiError(GitHubIssuesSourceError):
    """Raised for non-success GitHub HTTP responses."""

    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class GitHubIssuesResponseFormatError(GitHubIssuesSourceError):
    """Raised when a GitHub Issues payload cannot form a valid record."""


@dataclass(frozen=True)
class GitHubIssueRecord:
    """Minimal immutable GitHub Issue facts used for acquisition."""

    issue_id: int
    number: int
    title: str
    state: str
    html_url: str
    updated_at: datetime

    def __post_init__(self) -> None:
        if isinstance(self.issue_id, bool) or not isinstance(self.issue_id, int):
            raise ValueError("GitHub issue identifier must be an integer")
        if isinstance(self.number, bool) or not isinstance(self.number, int):
            raise ValueError("GitHub issue number must be an integer")
        for value, field_name in (
            (self.title, "GitHub issue title"),
            (self.state, "GitHub issue state"),
            (self.html_url, "GitHub issue URL"),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if self.updated_at.tzinfo is None or self.updated_at.utcoffset() is None:
            raise ValueError("GitHub issue updated timestamp must be timezone-aware")


@dataclass(frozen=True)
class GitHubIssuesReadConfiguration:
    """Transport configuration required to read GitHub Issues."""

    repository_owner: str
    repository_name: str
    request_timeout_seconds: int

    def __post_init__(self) -> None:
        if not self.repository_owner.strip():
            raise ValueError("GitHub repository owner must not be blank")
        if not self.repository_name.strip():
            raise ValueError("GitHub repository name must not be blank")
        if self.request_timeout_seconds <= 0:
            raise ValueError("GitHub request timeout must be greater than zero")


def github_issues_read_configuration_from_settings(
    app_settings: Settings,
) -> GitHubIssuesReadConfiguration:
    """Build acquisition configuration from backend settings."""
    owner = (app_settings.github_repository_owner or "").strip()
    name = (app_settings.github_repository_name or "").strip()
    if not owner or not name:
        raise GitHubIssuesConfigurationError(
            "GitHub Issues repository owner and name must be configured"
        )
    return GitHubIssuesReadConfiguration(
        repository_owner=owner,
        repository_name=name,
        request_timeout_seconds=app_settings.github_request_timeout_seconds,
    )


def fetch_github_issue_records(
    configuration: GitHubIssuesReadConfiguration,
) -> tuple[GitHubIssueRecord, ...]:
    """GET open GitHub Issues from the official REST API.

    Pagination is deferred: a single first-page GET is sufficient for the
    current two-issue public demo source.
    """
    repository = _repository_label(configuration)
    url = (
        f"{GITHUB_API_ORIGIN}/repos/"
        f"{configuration.repository_owner}/{configuration.repository_name}/issues"
    )
    try:
        with httpx.Client(
            timeout=configuration.request_timeout_seconds,
            headers={
                "Accept": GITHUB_ISSUES_ACCEPT,
                "User-Agent": GITHUB_ISSUES_USER_AGENT,
            },
        ) as client:
            response = client.get(url, params={"state": "open"})
    except httpx.TimeoutException as error:
        raise GitHubIssuesTransportError(
            "GitHub Issues request timed out after "
            f"{configuration.request_timeout_seconds} seconds for {repository}"
        ) from error
    except httpx.RequestError as error:
        raise GitHubIssuesTransportError(
            f"GitHub Issues request could not connect for {repository}"
        ) from error

    if response.status_code != 200:
        raise _api_error(response.status_code, repository)
    return parse_github_issues_json(response.text)


def parse_github_issues_json(source_text: str) -> tuple[GitHubIssueRecord, ...]:
    """Parse GitHub Issues JSON into source records, ignoring pull requests."""
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError:
        raise GitHubIssuesResponseFormatError(
            "GitHub Issues response must be valid JSON"
        ) from None

    if not isinstance(payload, list):
        raise GitHubIssuesResponseFormatError(
            "GitHub Issues response must be an array"
        )

    records: list[GitHubIssueRecord] = []
    for item in payload:
        if not isinstance(item, dict):
            raise GitHubIssuesResponseFormatError(
                "GitHub Issues item must be an object"
            )
        if "pull_request" in item:
            continue
        records.append(_parse_github_issue_record(item))
    return tuple(records)


def _parse_github_issue_record(item: dict[str, Any]) -> GitHubIssueRecord:
    try:
        return GitHubIssueRecord(
            issue_id=_required_int(item, "id"),
            number=_required_int(item, "number"),
            title=_required_string(item, "title"),
            state=_required_string(item, "state"),
            html_url=_required_string(item, "html_url"),
            updated_at=_parse_datetime(item, "updated_at"),
        )
    except ValueError as error:
        raise GitHubIssuesResponseFormatError(str(error)) from None


def _required_int(container: dict[str, Any], key: str) -> int:
    if key not in container:
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' is required"
        )
    value = container[key]
    if isinstance(value, bool) or not isinstance(value, int):
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' must be an integer"
        )
    return value


def _required_string(container: dict[str, Any], key: str) -> str:
    if key not in container:
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' is required"
        )
    value = container[key]
    if not isinstance(value, str):
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' must be a string"
        )
    return value


def _parse_datetime(container: dict[str, Any], key: str) -> datetime:
    value = _required_string(container, key)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' must be a timezone-aware ISO timestamp"
        ) from None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise GitHubIssuesResponseFormatError(
            f"GitHub Issues field '{key}' must be a timezone-aware ISO timestamp"
        )
    return parsed


def _api_error(status_code: int, repository: str) -> GitHubIssuesApiError:
    if status_code == 401:
        message = (
            f"GitHub Issues request was unauthorized (HTTP 401) for {repository}"
        )
    elif status_code == 403:
        message = f"GitHub Issues request was forbidden (HTTP 403) for {repository}"
    elif status_code == 404:
        message = (
            f"GitHub Issues repository was not found (HTTP 404) for {repository}"
        )
    elif status_code == 429:
        message = (
            f"GitHub Issues request was rate limited (HTTP 429) for {repository}"
        )
    else:
        message = f"GitHub Issues request failed (HTTP {status_code}) for {repository}"
    return GitHubIssuesApiError(message, status_code=status_code)


def _repository_label(configuration: GitHubIssuesReadConfiguration) -> str:
    return f"{configuration.repository_owner}/{configuration.repository_name}"
