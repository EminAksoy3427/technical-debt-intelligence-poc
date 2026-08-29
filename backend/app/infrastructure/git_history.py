from __future__ import annotations

import io
import re
import string
import tokenize
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path, PurePosixPath

from pydriller import Repository

_EXPLICIT_DEBT_PATTERN = re.compile(r"\b(?:technical|tech)\s+debt\b", re.IGNORECASE)


class GitHistorySourceError(RuntimeError):
    """Base error for the local Git-history source boundary."""


class GitRepositoryNotFoundError(GitHistorySourceError):
    """Raised when the requested repository path does not exist."""


class GitRepositoryInvalidError(GitHistorySourceError):
    """Raised when the requested path is not a Git working repository."""


class GitHistoryTraversalError(GitHistorySourceError):
    """Raised when PyDriller cannot traverse the requested repository."""


@dataclass(frozen=True)
class GitSatdFinding:
    """One explicit SATD comment added by one Git commit."""

    commit_hash: str
    relative_path: str
    added_line: int
    comment_text: str
    commit_timestamp: datetime

    def __post_init__(self) -> None:
        commit_hash = self.commit_hash.strip()
        if (
            len(commit_hash) not in (40, 64)
            or any(character not in string.hexdigits for character in commit_hash)
        ):
            raise ValueError("Git SATD finding must contain a full commit hash")
        if self.added_line < 1:
            raise ValueError("Git SATD finding added line must be positive")

        comment_text = self.comment_text.strip()
        if not comment_text.startswith("#"):
            raise ValueError("Git SATD finding text must be a Python comment")
        if "\n" in comment_text or "\r" in comment_text:
            raise ValueError("Git SATD finding comment must occupy one source line")
        if self.commit_timestamp.tzinfo is None:
            raise ValueError("Git commit timestamp must be timezone-aware")
        if self.commit_timestamp.utcoffset() is None:
            raise ValueError("Git commit timestamp must be timezone-aware")

        object.__setattr__(self, "commit_hash", commit_hash.lower())
        object.__setattr__(
            self,
            "relative_path",
            _normalize_repository_relative_path(self.relative_path),
        )
        object.__setattr__(self, "comment_text", comment_text)


def scan_git_satd_comments(repository_path: Path) -> tuple[GitSatdFinding, ...]:
    """Use PyDriller to find explicit SATD comments in added Python lines."""
    resolved_repository = repository_path.resolve()
    if not resolved_repository.exists():
        raise GitRepositoryNotFoundError(
            f"Git repository does not exist: {repository_path}"
        )
    if not resolved_repository.is_dir() or not (
        resolved_repository / ".git"
    ).exists():
        raise GitRepositoryInvalidError(
            f"Path is not a Git working repository: {repository_path}"
        )

    findings: list[GitSatdFinding] = []
    try:
        for commit in Repository(str(resolved_repository)).traverse_commits():
            commit_timestamp = commit.committer_date
            if (
                commit_timestamp is None
                or commit_timestamp.tzinfo is None
                or commit_timestamp.utcoffset() is None
            ):
                raise GitHistoryTraversalError(
                    f"Git commit timestamp must be timezone-aware: {commit.hash}"
                )

            for modification in commit.modified_files:
                path_value = modification.new_path or modification.old_path
                if path_value is None:
                    raise GitHistoryTraversalError(
                        f"Git modification has no repository path: {commit.hash}"
                    )
                relative_path = _normalize_repository_relative_path(path_value)
                if modification.new_path is None:
                    continue
                if PurePosixPath(relative_path).suffix.lower() != ".py":
                    continue

                source_code = modification.source_code
                if source_code is None:
                    continue
                comment_lines = _python_comment_lines(source_code)
                for added_line, _line_text in modification.diff_parsed["added"]:
                    comment_text = comment_lines.get(added_line)
                    if comment_text is None:
                        continue
                    if not _EXPLICIT_DEBT_PATTERN.search(comment_text):
                        continue
                    findings.append(
                        GitSatdFinding(
                            commit_hash=commit.hash,
                            relative_path=relative_path,
                            added_line=added_line,
                            comment_text=comment_text,
                            commit_timestamp=commit_timestamp,
                        )
                    )
    except GitHistorySourceError:
        raise
    except Exception as error:
        raise GitHistoryTraversalError(
            f"PyDriller could not traverse Git repository: {repository_path}"
        ) from error

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.commit_timestamp,
                finding.commit_hash,
                finding.relative_path,
                finding.added_line,
            ),
        )
    )


def _python_comment_lines(source_code: str) -> dict[int, str]:
    comments: dict[int, str] = {}
    tokens = tokenize.generate_tokens(io.StringIO(source_code).readline)
    try:
        for token in tokens:
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
    except (IndentationError, tokenize.TokenError):
        # Git may contain an intermediate syntactically incomplete Python file.
        # Any comments tokenized before the incomplete region remain source facts.
        pass
    return comments


def _normalize_repository_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized):
        raise GitHistoryTraversalError(
            "Git modified-file path must be repository-relative"
        )

    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise GitHistoryTraversalError(
            "Git modified-file path must be repository-relative"
        )

    parts = tuple(part for part in path.parts if part not in ("", "."))
    if not parts:
        raise GitHistoryTraversalError("Git modified-file path must not be blank")
    return str(PurePosixPath(*parts))
