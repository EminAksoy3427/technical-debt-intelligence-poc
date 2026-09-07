from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


@dataclass(frozen=True)
class CreateGitHubIssueCommand:
    owner: str
    repository: str
    title: str
    body: str

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (self.owner, self.repository, self.title, self.body)
        ):
            raise ValueError("GitHub issue executor command fields must not be blank")


class GitHubIssueExecutorOutcome(StrEnum):
    CREATED = "CREATED"
    REJECTED = "REJECTED"
    NOT_SENT = "NOT_SENT"
    TRANSPORT_UNKNOWN = "TRANSPORT_UNKNOWN"


@dataclass(frozen=True)
class GitHubIssueExecutorResult:
    outcome: GitHubIssueExecutorOutcome
    external_issue_id: int | None = None
    external_issue_number: int | None = None
    external_issue_url: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.outcome, GitHubIssueExecutorOutcome):
            raise ValueError("GitHub issue executor outcome must be supported")
        references = (
            self.external_issue_id,
            self.external_issue_number,
            self.external_issue_url,
        )
        if self.outcome is GitHubIssueExecutorOutcome.CREATED:
            if any(value is None for value in references):
                raise ValueError("CREATED result requires the GitHub issue reference")
            if not self.external_issue_url or not self.external_issue_url.strip():
                raise ValueError("CREATED result requires a nonblank issue URL")
        elif any(value is not None for value in references):
            raise ValueError("Non-CREATED result cannot claim a GitHub issue reference")


class GitHubIssueExecutor(Protocol):
    def create_issue(
        self,
        command: CreateGitHubIssueCommand,
    ) -> GitHubIssueExecutorResult: ...
