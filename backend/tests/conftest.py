import os
import shutil
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROLLED_SOURCE_REPOSITORY = (
    PROJECT_ROOT / "synthetic_repositories" / "repo-borealis-renderer"
)
BASELINE_DATE = "2026-08-20T10:00:00+00:00"
SATD_DATE = "2026-08-21T11:30:00+00:00"


@dataclass(frozen=True)
class ControlledGitRepository:
    path: Path
    relative_source_path: str
    baseline_commit_hash: str
    satd_commit_hash: str
    baseline_timestamp: datetime
    satd_timestamp: datetime


def materialize_controlled_git_repository(
    repository_path: Path,
) -> ControlledGitRepository:
    shutil.copytree(CONTROLLED_SOURCE_REPOSITORY, repository_path)
    source_path = repository_path / "renderer_client.py"
    baseline_source = source_path.read_text(encoding="utf-8")
    source_path.write_text(
        f"{baseline_source.rstrip()}\n\n"
        'DEBT_TERM = "technical debt"\n'
        "# TODO: improve renderer response validation\n",
        encoding="utf-8",
        newline="\n",
    )

    _run_git(repository_path, ["init", "--initial-branch=main"])
    for key, value in (
        ("user.name", "Controlled Fixture"),
        ("user.email", "controlled-fixture@synthetic.invalid"),
        ("core.autocrlf", "false"),
        ("core.filemode", "false"),
        ("commit.gpgsign", "false"),
    ):
        _run_git(repository_path, ["config", "--local", key, value])

    _run_git(repository_path, ["add", "--all"])
    _run_git(
        repository_path,
        ["commit", "-m", "Create deterministic baseline"],
        commit_date=BASELINE_DATE,
    )
    baseline_commit_hash = _run_git(
        repository_path,
        ["rev-parse", "HEAD"],
    ).stdout.strip()

    with source_path.open("a", encoding="utf-8", newline="\n") as source_file:
        source_file.write(
            "# TODO(technical debt): replace temporary compatibility workaround\n"
        )
    _run_git(repository_path, ["add", "renderer_client.py"])
    _run_git(
        repository_path,
        ["commit", "-m", "Document temporary compatibility workaround"],
        commit_date=SATD_DATE,
    )
    satd_commit_hash = _run_git(
        repository_path,
        ["rev-parse", "HEAD"],
    ).stdout.strip()

    return ControlledGitRepository(
        path=repository_path,
        relative_source_path="renderer_client.py",
        baseline_commit_hash=baseline_commit_hash,
        satd_commit_hash=satd_commit_hash,
        baseline_timestamp=datetime.fromisoformat(BASELINE_DATE),
        satd_timestamp=datetime.fromisoformat(SATD_DATE),
    )


@pytest.fixture
def controlled_git_repository_factory() -> Callable[
    [Path], ControlledGitRepository
]:
    return materialize_controlled_git_repository


@pytest.fixture
def controlled_git_repository(
    tmp_path: Path,
    controlled_git_repository_factory: Callable[[Path], ControlledGitRepository],
) -> ControlledGitRepository:
    return controlled_git_repository_factory(
        tmp_path / "repo-borealis-renderer"
    )


def _run_git(
    repository_path: Path,
    arguments: list[str],
    *,
    commit_date: str | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    if commit_date is not None:
        environment["GIT_AUTHOR_DATE"] = commit_date
        environment["GIT_COMMITTER_DATE"] = commit_date

    try:
        return subprocess.run(
            ["git", *arguments],
            cwd=repository_path,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            shell=False,
        )
    except FileNotFoundError:
        raise RuntimeError("Git CLI is required for the controlled fixture") from None
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip()
        raise RuntimeError(
            f"Controlled Git fixture command failed: git {' '.join(arguments)}"
            f": {detail}"
        ) from error
