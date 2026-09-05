from typing import Final

from app.connectors.contracts import (
    ConnectorDescriptor,
    ConnectorRegistration,
    SourceObservation,
)
from app.domain.signals import SourceObservationRef
from app.infrastructure.github_issues import (
    GitHubIssueRecord,
    GitHubIssuesReadConfiguration,
    fetch_github_issue_records,
)

GITHUB_ISSUES_SOURCE_SYSTEM: Final = "github-issues"

GITHUB_ISSUES_CONNECTOR_DESCRIPTOR: Final = ConnectorDescriptor(
    connector_id="github-issues",
    display_name="GitHub Issues",
    version="1.0.0",
    source_system=GITHUB_ISSUES_SOURCE_SYSTEM,
    transport="https",
    read_only=True,
)


def acquire_github_issue_observations(
    configuration: GitHubIssuesReadConfiguration,
) -> tuple[SourceObservation[GitHubIssueRecord], ...]:
    """Acquire GitHub Issue records without canonical interpretation."""
    records = fetch_github_issue_records(configuration)
    return tuple(
        SourceObservation(
            provenance=SourceObservationRef(
                source_system=GITHUB_ISSUES_SOURCE_SYSTEM,
                source_record_id=str(record.issue_id),
            ),
            observed_at=record.updated_at,
            record=record,
        )
        for record in records
    )


GITHUB_ISSUES_CONNECTOR: Final = ConnectorRegistration(
    descriptor=GITHUB_ISSUES_CONNECTOR_DESCRIPTOR,
    acquire=acquire_github_issue_observations,
)
