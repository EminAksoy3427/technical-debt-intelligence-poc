from unittest.mock import Mock

import httpx
from pydantic import SecretStr

from app.actions.github_issue_verifier import GitHubIssueReadOutcome
from app.infrastructure.github_issue_verifier import (
    GitHubIssueVerifierConfiguration,
    HttpGitHubIssueVerifier,
)


def _client(response: Mock) -> Mock:
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.get.return_value = response
    client.post = Mock(side_effect=AssertionError("Verifier must never POST"))
    return client


def test_get_issue_uses_get_only_and_keeps_token_out_of_repr(monkeypatch) -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "id": 99,
        "number": 4,
        "html_url": "https://github.com/demo/repo/issues/4",
        "title": "Exact title",
        "body": "Exact body",
        "ignored_raw": "not persisted",
    }
    client = _client(response)
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    verifier = HttpGitHubIssueVerifier(
        GitHubIssueVerifierConfiguration(SecretStr("secret-token"), 2, 5)
    )

    result = verifier.get_issue("demo", "repo", 4)

    assert result.outcome is GitHubIssueReadOutcome.FOUND
    assert result.issue is not None
    assert result.issue.issue_number == 4
    assert result.issue.is_pull_request is False
    client.get.assert_called_once_with(
        "https://api.github.com/repos/demo/repo/issues/4",
        params=None,
    )
    client.post.assert_not_called()
    assert "secret-token" not in repr(verifier._configuration)
    assert not hasattr(result, "raw_response")


def test_search_is_get_only_and_transport_error_is_unavailable(monkeypatch) -> None:
    client = Mock()
    client.__enter__ = Mock(return_value=client)
    client.__exit__ = Mock(return_value=False)
    client.get.side_effect = httpx.ConnectError("boom")
    monkeypatch.setattr(httpx, "Client", Mock(return_value=client))
    verifier = HttpGitHubIssueVerifier(
        GitHubIssueVerifierConfiguration(SecretStr("fake"), 2, 5)
    )

    result = verifier.find_issues_by_marker(
        "demo", "repo", "tdiq-action-proposal:abc"
    )

    assert result.outcome is GitHubIssueReadOutcome.UNAVAILABLE
    assert result.issues == ()
    client.post.assert_not_called()


def test_pull_request_payload_is_flagged(monkeypatch) -> None:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "id": 1,
        "number": 9,
        "html_url": "https://github.com/demo/repo/pull/9",
        "title": "PR title",
        "body": "body",
        "pull_request": {"url": "https://api.github.com/repos/demo/repo/pulls/9"},
    }
    monkeypatch.setattr(httpx, "Client", Mock(return_value=_client(response)))
    verifier = HttpGitHubIssueVerifier(
        GitHubIssueVerifierConfiguration(SecretStr("fake"), 2, 5)
    )

    result = verifier.get_issue("demo", "repo", 9)

    assert result.issue is not None
    assert result.issue.is_pull_request is True
