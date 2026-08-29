import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from app.infrastructure.git_history import (
    GitHistorySourceError,
    GitHistoryTraversalError,
    GitRepositoryInvalidError,
    GitRepositoryNotFoundError,
    GitSatdFinding,
    scan_git_satd_comments,
)


def test_git_cli_is_invokable() -> None:
    completed = subprocess.run(
        ["git", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        shell=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.startswith("git version ")


def test_controlled_real_git_history_is_deterministic(
    tmp_path: Path,
    controlled_git_repository,
    controlled_git_repository_factory,
) -> None:
    repeated_repository = controlled_git_repository_factory(
        tmp_path / "repeated-repository"
    )

    assert repeated_repository.baseline_commit_hash == (
        controlled_git_repository.baseline_commit_hash
    )
    assert repeated_repository.satd_commit_hash == (
        controlled_git_repository.satd_commit_hash
    )
    assert scan_git_satd_comments(repeated_repository.path) == (
        scan_git_satd_comments(controlled_git_repository.path)
    )


def test_pydriller_finds_only_the_explicit_satd_comment(
    controlled_git_repository,
) -> None:
    findings = scan_git_satd_comments(controlled_git_repository.path)
    baseline_findings = tuple(
        finding
        for finding in findings
        if finding.commit_hash == controlled_git_repository.baseline_commit_hash
    )
    satd_commit_findings = tuple(
        finding
        for finding in findings
        if finding.commit_hash == controlled_git_repository.satd_commit_hash
    )

    assert baseline_findings == ()
    assert len(satd_commit_findings) == 1
    assert findings == satd_commit_findings


def test_git_finding_contains_only_portable_source_facts(
    controlled_git_repository,
) -> None:
    finding = scan_git_satd_comments(controlled_git_repository.path)[0]

    assert len(finding.commit_hash) == 40
    assert finding.commit_hash == controlled_git_repository.satd_commit_hash
    assert finding.relative_path == controlled_git_repository.relative_source_path
    assert finding.added_line > 0
    assert finding.comment_text == (
        "# TODO(technical debt): replace temporary compatibility workaround"
    )
    assert finding.commit_timestamp == controlled_git_repository.satd_timestamp
    assert finding.commit_timestamp.utcoffset() is not None
    assert str(controlled_git_repository.path) not in repr(finding)
    assert not Path(finding.relative_path).is_absolute()
    assert ":" not in finding.relative_path
    assert "\\" not in finding.relative_path


def test_generic_todo_and_string_literal_are_not_satd(
    controlled_git_repository,
) -> None:
    findings = scan_git_satd_comments(controlled_git_repository.path)

    assert all(
        "improve renderer response validation" not in item.comment_text
        for item in findings
    )
    assert len(findings) == 1


def test_missing_repository_fails_explicitly(tmp_path: Path) -> None:
    with pytest.raises(GitRepositoryNotFoundError, match="does not exist"):
        scan_git_satd_comments(tmp_path / "missing-repository")


def test_non_git_directory_fails_explicitly(tmp_path: Path) -> None:
    repository_path = tmp_path / "not-a-git-repository"
    repository_path.mkdir()

    with pytest.raises(GitRepositoryInvalidError, match="not a Git"):
        scan_git_satd_comments(repository_path)


def test_pydriller_traversal_failure_is_wrapped_with_its_cause(
    monkeypatch: pytest.MonkeyPatch,
    controlled_git_repository,
) -> None:
    class FailedRepository:
        def __init__(self, _repository_path: str) -> None:
            pass

        def traverse_commits(self):
            raise OSError("synthetic traversal failure")

    monkeypatch.setattr(
        "app.infrastructure.git_history.Repository",
        FailedRepository,
    )

    with pytest.raises(
        GitHistoryTraversalError,
        match="PyDriller could not traverse",
    ) as error:
        scan_git_satd_comments(controlled_git_repository.path)

    assert isinstance(error.value.__cause__, OSError)


def test_finding_rejects_nonportable_path_and_naive_timestamp() -> None:
    with pytest.raises(GitHistorySourceError, match="repository-relative"):
        GitSatdFinding(
            commit_hash="a" * 40,
            relative_path="C:/local/repository/source.py",
            added_line=4,
            comment_text="# technical debt: temporary path",
            commit_timestamp=datetime.fromisoformat("2026-08-21T11:30:00+00:00"),
        )

    with pytest.raises(ValueError, match="timezone-aware"):
        GitSatdFinding(
            commit_hash="a" * 40,
            relative_path="source.py",
            added_line=4,
            comment_text="# technical debt: temporary path",
            commit_timestamp=datetime(2026, 8, 21, 11, 30),
        )
