from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.actions.github_issue_verifier import (
    GitHubIssueReadOutcome,
    GitHubIssueReadResult,
    GitHubIssueSearchResult,
    ObservedGitHubIssue,
)

GITHUB_API_ORIGIN = "https://api.github.com"


@dataclass(frozen=True)
class GitHubIssueVerifierConfiguration:
    token: SecretStr
    connect_timeout_seconds: int
    request_timeout_seconds: int


class HttpGitHubIssueVerifier:
    """Dedicated zero-retry GitHub issue reader, separate from acquisition and WRITE."""

    def __init__(self, configuration: GitHubIssueVerifierConfiguration) -> None:
        self._configuration = configuration

    def get_issue(
        self,
        owner: str,
        repository: str,
        issue_number: int,
    ) -> GitHubIssueReadResult:
        response = self._get(
            f"{GITHUB_API_ORIGIN}/repos/{owner}/{repository}/issues/{issue_number}"
        )
        if response is None:
            return GitHubIssueReadResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
        if response.status_code == 404:
            return GitHubIssueReadResult(outcome=GitHubIssueReadOutcome.NOT_FOUND)
        if response.status_code != 200:
            return GitHubIssueReadResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
        issue = _parse_issue(response)
        if issue is None:
            return GitHubIssueReadResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
        return GitHubIssueReadResult(
            outcome=GitHubIssueReadOutcome.FOUND,
            issue=issue,
        )

    def find_issues_by_marker(
        self,
        owner: str,
        repository: str,
        marker: str,
    ) -> GitHubIssueSearchResult:
        query = f'repo:{owner}/{repository} "{marker}" in:body'
        response = self._get(
            f"{GITHUB_API_ORIGIN}/search/issues",
            params={"q": query},
        )
        if response is None or response.status_code != 200:
            return GitHubIssueSearchResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
        return _parse_search(response)

    def _get(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> httpx.Response | None:
        timeout = httpx.Timeout(
            self._configuration.request_timeout_seconds,
            connect=self._configuration.connect_timeout_seconds,
        )
        try:
            with httpx.Client(
                timeout=timeout,
                transport=httpx.HTTPTransport(retries=0),
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": (
                        "Bearer " + self._configuration.token.get_secret_value()
                    ),
                    "User-Agent": "technical-debt-intelligence-poc",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            ) as client:
                return client.get(url, params=params)
        except httpx.RequestError:
            return None


def _parse_search(response: httpx.Response) -> GitHubIssueSearchResult:
    try:
        payload: Any = response.json()
        items = payload["items"]
        if not isinstance(items, list):
            raise ValueError
    except (ValueError, TypeError, KeyError):
        return GitHubIssueSearchResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
    issues: list[ObservedGitHubIssue] = []
    for item in items:
        issue = _parse_issue_payload(item)
        if issue is None:
            return GitHubIssueSearchResult(outcome=GitHubIssueReadOutcome.UNAVAILABLE)
        issues.append(issue)
    if not issues:
        return GitHubIssueSearchResult(outcome=GitHubIssueReadOutcome.NOT_FOUND)
    return GitHubIssueSearchResult(
        outcome=GitHubIssueReadOutcome.FOUND,
        issues=tuple(issues),
    )


def _parse_issue(response: httpx.Response) -> ObservedGitHubIssue | None:
    try:
        payload: Any = response.json()
    except ValueError:
        return None
    return _parse_issue_payload(payload)


def _parse_issue_payload(payload: Any) -> ObservedGitHubIssue | None:
    if not isinstance(payload, dict):
        return None
    try:
        issue_id = payload["id"]
        number = payload["number"]
        html_url = payload["html_url"]
        title = payload["title"]
        body = payload.get("body")
        if body is None:
            body = ""
        if (
            isinstance(issue_id, bool)
            or not isinstance(issue_id, int)
            or isinstance(number, bool)
            or not isinstance(number, int)
            or not isinstance(html_url, str)
            or not html_url.strip()
            or not isinstance(title, str)
            or not isinstance(body, str)
        ):
            raise ValueError
        return ObservedGitHubIssue(
            issue_id=issue_id,
            issue_number=number,
            html_url=html_url,
            title=title,
            body=body,
            is_pull_request="pull_request" in payload,
        )
    except (ValueError, TypeError, KeyError):
        return None
