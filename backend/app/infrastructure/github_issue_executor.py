from dataclasses import dataclass
from typing import Any

import httpx
from pydantic import SecretStr

from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
    GitHubIssueExecutorResult,
)

GITHUB_API_ORIGIN = "https://api.github.com"


@dataclass(frozen=True)
class GitHubIssueExecutorConfiguration:
    token: SecretStr
    connect_timeout_seconds: int
    request_timeout_seconds: int


class HttpGitHubIssueExecutor:
    """Dedicated zero-retry GitHub issue writer, separate from acquisition."""

    def __init__(self, configuration: GitHubIssueExecutorConfiguration) -> None:
        self._configuration = configuration

    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult:
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
                        "Bearer "
                        + self._configuration.token.get_secret_value()
                    ),
                    "User-Agent": "technical-debt-intelligence-poc",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            ) as client:
                response = client.post(
                    f"{GITHUB_API_ORIGIN}/repos/{command.owner}/"
                    f"{command.repository}/issues",
                    json={"title": command.title, "body": command.body},
                )
        except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
            return GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.NOT_SENT
            )
        except httpx.RequestError:
            return GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
            )

        if response.status_code == 201:
            return _created_result(response)
        if 400 <= response.status_code < 500:
            return GitHubIssueExecutorResult(
                outcome=GitHubIssueExecutorOutcome.REJECTED
            )
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
        )


def _created_result(response: httpx.Response) -> GitHubIssueExecutorResult:
    try:
        payload: Any = response.json()
        issue_id = payload["id"]
        number = payload["number"]
        html_url = payload["html_url"]
        if (
            isinstance(issue_id, bool)
            or not isinstance(issue_id, int)
            or isinstance(number, bool)
            or not isinstance(number, int)
            or not isinstance(html_url, str)
            or not html_url.strip()
        ):
            raise ValueError
    except (ValueError, TypeError, KeyError):
        return GitHubIssueExecutorResult(
            outcome=GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
        )
    return GitHubIssueExecutorResult(
        outcome=GitHubIssueExecutorOutcome.CREATED,
        external_issue_id=issue_id,
        external_issue_number=number,
        external_issue_url=html_url,
    )
