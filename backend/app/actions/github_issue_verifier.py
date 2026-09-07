from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True)
class ObservedGitHubIssue:
    """Bounded GitHub issue facts used for read-back comparison."""

    issue_id: int
    issue_number: int
    html_url: str
    title: str
    body: str
    is_pull_request: bool

    def __post_init__(self) -> None:
        if isinstance(self.issue_id, bool) or not isinstance(self.issue_id, int):
            raise ValueError("Observed GitHub issue identifier must be an integer")
        if isinstance(self.issue_number, bool) or not isinstance(
            self.issue_number, int
        ):
            raise ValueError("Observed GitHub issue number must be an integer")
        if not self.html_url.strip():
            raise ValueError("Observed GitHub issue URL must not be blank")
        if not isinstance(self.title, str):
            raise ValueError("Observed GitHub issue title must be a string")
        if not isinstance(self.body, str):
            raise ValueError("Observed GitHub issue body must be a string")


class GitHubIssueReadOutcome(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    UNAVAILABLE = "UNAVAILABLE"


@dataclass(frozen=True)
class GitHubIssueReadResult:
    outcome: GitHubIssueReadOutcome
    issue: ObservedGitHubIssue | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, GitHubIssueReadOutcome):
            raise ValueError("GitHub issue read outcome must be supported")
        if self.outcome is GitHubIssueReadOutcome.FOUND:
            if self.issue is None:
                raise ValueError("FOUND read result requires an observed issue")
        elif self.issue is not None:
            raise ValueError("Non-FOUND read result cannot claim an observed issue")


@dataclass(frozen=True)
class GitHubIssueSearchResult:
    outcome: GitHubIssueReadOutcome
    issues: tuple[ObservedGitHubIssue, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, GitHubIssueReadOutcome):
            raise ValueError("GitHub issue search outcome must be supported")
        if self.outcome is GitHubIssueReadOutcome.UNAVAILABLE:
            if self.issues:
                raise ValueError("UNAVAILABLE search cannot claim observed issues")
        elif self.outcome is GitHubIssueReadOutcome.NOT_FOUND:
            if self.issues:
                raise ValueError("NOT_FOUND search cannot claim observed issues")
        elif self.outcome is GitHubIssueReadOutcome.FOUND and not self.issues:
            raise ValueError("FOUND search result requires at least one issue")


class GitHubIssueVerifier(Protocol):
    """Dedicated action-plane read-back port. GET only. Never mutates GitHub."""

    def get_issue(
        self,
        owner: str,
        repository: str,
        issue_number: int,
    ) -> GitHubIssueReadResult: ...

    def find_issues_by_marker(
        self,
        owner: str,
        repository: str,
        marker: str,
    ) -> GitHubIssueSearchResult: ...
