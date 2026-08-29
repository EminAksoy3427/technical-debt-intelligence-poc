from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


class SemgrepError(RuntimeError):
    """Base error for the local Semgrep boundary."""


class SemgrepExecutableNotFoundError(SemgrepError):
    """Raised when the configured Semgrep executable cannot be started."""


class SemgrepExecutionError(SemgrepError):
    """Raised when the Semgrep process does not complete successfully."""


class SemgrepOutputError(SemgrepError):
    """Raised when Semgrep output does not match its public JSON contract."""


class SemgrepScanError(SemgrepError):
    """Raised when Semgrep reports one or more scan errors."""


@dataclass(frozen=True)
class SemgrepFinding:
    """The small source-specific boundary read from Semgrep public JSON output."""

    rule_id: str
    relative_path: str
    start_line: int
    start_column: int
    end_line: int
    end_column: int
    message: str
    severity: str

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise ValueError("Semgrep rule identifier must not be blank")
        if not self.message.strip():
            raise ValueError("Semgrep finding message must not be blank")
        if not self.severity.strip():
            raise ValueError("Semgrep finding severity must not be blank")

        location_values = (
            self.start_line,
            self.start_column,
            self.end_line,
            self.end_column,
        )
        if any(value < 1 for value in location_values):
            raise ValueError("Semgrep finding locations must be positive")
        if (self.end_line, self.end_column) < (
            self.start_line,
            self.start_column,
        ):
            raise ValueError("Semgrep finding end location must not precede its start")

        object.__setattr__(
            self,
            "relative_path",
            _normalize_repository_relative_path(self.relative_path),
        )


def scan_semgrep_repository(
    repository_path: Path,
    rules_path: Path,
    *,
    executable: str = "semgrep",
) -> tuple[SemgrepFinding, ...]:
    """Run Semgrep CE locally with repository-controlled rules."""
    command = [
        executable,
        "scan",
        "--config",
        str(rules_path.resolve()),
        "--json",
        "--metrics=off",
        "--no-rewrite-rule-ids",
        ".",
    ]
    try:
        completed = subprocess.run(
            command,
            cwd=repository_path.resolve(),
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
            shell=False,
        )
    except FileNotFoundError:
        raise SemgrepExecutableNotFoundError(
            f"Semgrep executable was not found: {executable}"
        ) from None
    except OSError as error:
        raise SemgrepExecutionError(
            f"Semgrep process could not be started: {error}"
        ) from error

    try:
        findings = parse_semgrep_json(completed.stdout)
    except SemgrepScanError:
        raise
    except SemgrepOutputError:
        if completed.returncode != 0:
            raise SemgrepExecutionError(
                _execution_failure_message(completed)
            ) from None
        raise

    if completed.returncode != 0:
        raise SemgrepExecutionError(_execution_failure_message(completed))

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.relative_path,
                finding.rule_id,
                finding.start_line,
                finding.start_column,
                finding.end_line,
                finding.end_column,
            ),
        )
    )


def parse_semgrep_json(output: str) -> tuple[SemgrepFinding, ...]:
    """Parse only the public Semgrep JSON fields required by ingestion."""
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        raise SemgrepOutputError("Semgrep did not return valid JSON output") from None

    if not isinstance(payload, dict):
        raise SemgrepOutputError("Semgrep JSON output must be an object")

    errors = _required_list(payload, "errors")
    if errors:
        raise SemgrepScanError(_scan_error_message(errors))

    results = _required_list(payload, "results")
    return tuple(_parse_finding(result) for result in results)


def _parse_finding(value: Any) -> SemgrepFinding:
    finding = _required_object(value, "finding")
    start = _required_object(finding.get("start"), "finding.start")
    end = _required_object(finding.get("end"), "finding.end")
    extra = _required_object(finding.get("extra"), "finding.extra")

    try:
        return SemgrepFinding(
            rule_id=_required_string(finding, "check_id", "finding"),
            relative_path=_required_string(finding, "path", "finding"),
            start_line=_required_integer(start, "line", "finding.start"),
            start_column=_required_integer(start, "col", "finding.start"),
            end_line=_required_integer(end, "line", "finding.end"),
            end_column=_required_integer(end, "col", "finding.end"),
            message=_required_string(extra, "message", "finding.extra"),
            severity=_required_string(extra, "severity", "finding.extra"),
        )
    except ValueError as error:
        raise SemgrepOutputError(str(error)) from error


def _required_list(container: dict[str, Any], key: str) -> list[Any]:
    value = container.get(key)
    if not isinstance(value, list):
        raise SemgrepOutputError(f"Semgrep JSON field '{key}' must be an array")
    return value


def _required_object(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SemgrepOutputError(
            f"Semgrep JSON field '{field_name}' must be an object"
        )
    return value


def _required_string(
    container: dict[str, Any],
    key: str,
    parent_name: str,
) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise SemgrepOutputError(
            f"Semgrep JSON field '{parent_name}.{key}' must be a string"
        )
    return value


def _required_integer(
    container: dict[str, Any],
    key: str,
    parent_name: str,
) -> int:
    value = container.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise SemgrepOutputError(
            f"Semgrep JSON field '{parent_name}.{key}' must be an integer"
        )
    return value


def _normalize_repository_relative_path(value: str) -> str:
    normalized = value.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", normalized):
        raise ValueError("Semgrep finding path must be repository-relative")

    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Semgrep finding path must be repository-relative")

    parts = tuple(part for part in path.parts if part not in ("", "."))
    if not parts:
        raise ValueError("Semgrep finding path must not be blank")
    return str(PurePosixPath(*parts))


def _scan_error_message(errors: list[Any]) -> str:
    summaries: list[str] = []
    for error in errors:
        if not isinstance(error, dict):
            summaries.append("unknown scan error")
            continue
        error_type = error.get("type", "unknown")
        detail = (
            error.get("message")
            or error.get("short_msg")
            or error.get("long_msg")
            or ""
        )
        summaries.append(f"{error_type}: {detail}".strip())
    return f"Semgrep reported scan errors: {'; '.join(summaries)}"


def _execution_failure_message(completed: subprocess.CompletedProcess[str]) -> str:
    detail = completed.stderr.strip()
    if len(detail) > 500:
        detail = f"{detail[:497]}..."
    suffix = f": {detail}" if detail else ""
    return f"Semgrep exited with status {completed.returncode}{suffix}"
