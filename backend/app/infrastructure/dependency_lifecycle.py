import json
from dataclasses import dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class DependencyLifecycleSourceError(RuntimeError):
    """Base error for the controlled dependency lifecycle source boundary."""


class DependencyLifecycleSourceFormatError(DependencyLifecycleSourceError):
    """Raised when source JSON cannot form a valid lifecycle finding."""


class DependencyLifecycleStatus(StrEnum):
    END_OF_LIFE = "END_OF_LIFE"


@dataclass(frozen=True)
class DependencyLifecycleFinding:
    """A source-specific dependency lifecycle observation."""

    source_record_id: str
    affected_asset_key: str
    component_name: str
    component_version: str
    lifecycle_status: DependencyLifecycleStatus
    eol_date: date
    observed_at: datetime
    message: str

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.source_record_id, "Dependency lifecycle source record identifier"),
            (self.affected_asset_key, "Dependency lifecycle affected asset key"),
            (self.component_name, "Dependency lifecycle component name"),
            (self.component_version, "Dependency lifecycle component version"),
            (self.message, "Dependency lifecycle message"),
        ):
            if not value.strip():
                raise ValueError(f"{field_name} must not be blank")
        if not isinstance(self.lifecycle_status, DependencyLifecycleStatus):
            raise ValueError("Dependency lifecycle status must be supported")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError(
                "Dependency lifecycle observation timestamp must be timezone-aware"
            )


def load_dependency_lifecycle_findings(
    source_path: Path,
) -> tuple[DependencyLifecycleFinding, ...]:
    """Read controlled dependency lifecycle source JSON."""
    try:
        source_text = source_path.read_text(encoding="utf-8")
    except OSError as error:
        raise DependencyLifecycleSourceError(
            f"Dependency lifecycle source could not be read: {source_path}"
        ) from error
    return parse_dependency_lifecycle_json(source_text)


def parse_dependency_lifecycle_json(
    source_text: str,
) -> tuple[DependencyLifecycleFinding, ...]:
    """Parse the required fields from a controlled lifecycle export."""
    try:
        payload = json.loads(source_text)
    except (json.JSONDecodeError, TypeError):
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle source must be valid JSON"
        ) from None

    if not isinstance(payload, dict):
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle source JSON must be an object"
        )

    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle source field 'findings' must be an array"
        )

    parsed_findings = tuple(_parse_finding(value) for value in findings)
    source_record_ids = {finding.source_record_id for finding in parsed_findings}
    if len(source_record_ids) != len(parsed_findings):
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle source record identifiers must be unique"
        )
    return parsed_findings


def _parse_finding(value: Any) -> DependencyLifecycleFinding:
    if not isinstance(value, dict):
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle finding must be an object"
        )

    try:
        return DependencyLifecycleFinding(
            source_record_id=_required_string(value, "source_record_id"),
            affected_asset_key=_required_string(value, "affected_asset_key"),
            component_name=_required_string(value, "component_name"),
            component_version=_required_string(value, "component_version"),
            lifecycle_status=DependencyLifecycleStatus(
                _required_string(value, "lifecycle_status")
            ),
            eol_date=_parse_date(value, "eol_date"),
            observed_at=_parse_datetime(value, "observed_at"),
            message=_required_string(value, "message"),
        )
    except ValueError as error:
        raise DependencyLifecycleSourceFormatError(str(error)) from None


def _required_string(container: dict[str, Any], key: str) -> str:
    value = container.get(key)
    if not isinstance(value, str):
        raise DependencyLifecycleSourceFormatError(
            f"Dependency lifecycle source field '{key}' must be a string"
        )
    return value


def _parse_date(container: dict[str, Any], key: str) -> date:
    value = _required_string(container, key)
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise DependencyLifecycleSourceFormatError(
            f"Dependency lifecycle source field '{key}' must be an ISO date"
        ) from None


def _parse_datetime(container: dict[str, Any], key: str) -> datetime:
    value = _required_string(container, key)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise DependencyLifecycleSourceFormatError(
            f"Dependency lifecycle source field '{key}' must be an ISO timestamp"
        ) from None

    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise DependencyLifecycleSourceFormatError(
            "Dependency lifecycle observation timestamp must be timezone-aware"
        )
    return parsed
