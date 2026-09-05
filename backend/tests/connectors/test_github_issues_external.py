import pytest

from app.connectors.contracts import SourceObservation
from app.connectors.github_issues import acquire_github_issue_observations
from app.core.config import Settings
from app.infrastructure.github_issues import (
    GitHubIssueRecord,
    GitHubIssuesConfigurationError,
    github_issues_read_configuration_from_settings,
)

ISSUE_ONE_TITLE = "[TDI-DEMO] Catalog client request has no explicit timeout"
ISSUE_TWO_TITLE = "[TDI-DEMO] Process-local cache should be externalized"


@pytest.mark.external
def test_public_demo_github_issues_are_acquired() -> None:
    try:
        configuration = github_issues_read_configuration_from_settings(
            Settings(_env_file=None)
        )
    except GitHubIssuesConfigurationError:
        pytest.skip("GitHub Issues repository owner and name are not configured")

    observations = acquire_github_issue_observations(configuration)

    assert observations
    assert all(isinstance(item, SourceObservation) for item in observations)
    assert all(isinstance(item.record, GitHubIssueRecord) for item in observations)

    by_number = {item.record.number: item for item in observations}
    assert 1 in by_number
    assert 2 in by_number

    issue_one = by_number[1]
    issue_two = by_number[2]

    assert issue_one.record.title == ISSUE_ONE_TITLE
    assert issue_one.record.state == "open"
    assert issue_one.provenance.source_system == "github-issues"
    assert issue_one.provenance.source_record_id == str(issue_one.record.issue_id)
    assert issue_one.provenance.source_record_id != str(issue_one.record.number)
    assert issue_one.observed_at == issue_one.record.updated_at
    assert issue_one.observed_at.tzinfo is not None

    assert issue_two.record.title == ISSUE_TWO_TITLE
    assert issue_two.record.state == "open"
    assert issue_two.provenance.source_system == "github-issues"
    assert issue_two.provenance.source_record_id == str(issue_two.record.issue_id)
    assert issue_two.provenance.source_record_id != str(issue_two.record.number)
    assert issue_two.observed_at == issue_two.record.updated_at
    assert issue_two.observed_at.tzinfo is not None

    print(
        "GitHub external proof: "
        f"number={issue_one.record.number} "
        f"id={issue_one.record.issue_id} "
        f"title={issue_one.record.title!r} "
        f"state={issue_one.record.state} "
        f"updated_at={issue_one.record.updated_at.isoformat()} "
        f"source_record_id={issue_one.provenance.source_record_id}"
    )
    print(
        "GitHub external proof: "
        f"number={issue_two.record.number} "
        f"id={issue_two.record.issue_id} "
        f"title={issue_two.record.title!r} "
        f"state={issue_two.record.state} "
        f"updated_at={issue_two.record.updated_at.isoformat()} "
        f"source_record_id={issue_two.provenance.source_record_id}"
    )
