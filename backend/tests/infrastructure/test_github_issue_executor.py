from unittest.mock import Mock

import httpx
from pydantic import SecretStr

from app.actions.github_issue_executor import (
    CreateGitHubIssueCommand,
    GitHubIssueExecutorOutcome,
)
from app.infrastructure.github_issue_executor import (
    GitHubIssueExecutorConfiguration,
    HttpGitHubIssueExecutor,
)


def test_executor_posts_exact_payload_once_and_returns_safe_created_result(
    monkeypatch,
) -> None:
    response = Mock()
    response.status_code = 201
    response.json.return_value = {
        "id": 99,
        "number": 4,
        "html_url": "https://github.com/demo/repo/issues/4",
        "ignored_raw_body": "not persisted",
    }
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.post.return_value = response
    constructor = Mock(return_value=client)
    monkeypatch.setattr(httpx, "Client", constructor)
    executor = HttpGitHubIssueExecutor(
        GitHubIssueExecutorConfiguration(SecretStr("secret-token"), 2, 5)
    )
    command = CreateGitHubIssueCommand("demo", "repo", "Exact title", "Exact body")

    result = executor.create_issue(command)

    assert result.outcome is GitHubIssueExecutorOutcome.CREATED
    assert result.external_issue_number == 4
    client.post.assert_called_once_with(
        "https://api.github.com/repos/demo/repo/issues",
        json={"title": "Exact title", "body": "Exact body"},
    )
    assert "secret-token" not in repr(executor._configuration)
    assert not hasattr(result, "raw_response")


def test_ambiguous_server_response_is_never_retried(monkeypatch) -> None:
    response = Mock(status_code=503)
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.post.return_value = response
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    executor = HttpGitHubIssueExecutor(
        GitHubIssueExecutorConfiguration(SecretStr("fake"), 2, 5)
    )

    result = executor.create_issue(
        CreateGitHubIssueCommand("demo", "repo", "title", "body")
    )

    assert result.outcome is GitHubIssueExecutorOutcome.TRANSPORT_UNKNOWN
    assert client.post.call_count == 1
