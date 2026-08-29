from datetime import date, datetime
from pathlib import Path

import pytest

from app.infrastructure.dependency_lifecycle import (
    DependencyLifecycleFinding,
    DependencyLifecycleSourceFormatError,
    DependencyLifecycleStatus,
    load_dependency_lifecycle_findings,
    parse_dependency_lifecycle_json,
)

SOURCE_PATH = (
    Path(__file__).resolve().parents[3]
    / "synthetic_sources"
    / "dependency_lifecycle_findings.json"
)


def test_controlled_dependency_lifecycle_source_parses_to_source_specific_finding() -> (
    None
):
    findings = load_dependency_lifecycle_findings(SOURCE_PATH)

    assert findings == (
        DependencyLifecycleFinding(
            source_record_id="dep-lifecycle-borealis-renderer-001",
            affected_asset_key="repo-borealis-renderer",
            component_name="fictional-render-exporter",
            component_version="2.4.1",
            lifecycle_status=DependencyLifecycleStatus.END_OF_LIFE,
            eol_date=date(2026, 6, 30),
            observed_at=datetime.fromisoformat("2026-08-01T10:00:00+00:00"),
            message=(
                "Synthetic lifecycle export reports fictional-render-exporter "
                "2.4.1 as end of life."
            ),
        ),
    )


@pytest.mark.parametrize(
    "source_text",
    [
        "not-json",
        "[]",
        "{}",
        '{"findings": [{}]}',
        (
            '{"findings": [{"source_record_id": "finding-001", '
            '"affected_asset_key": "repo-borealis-renderer", '
            '"component_name": "fictional-render-exporter", '
            '"component_version": "2.4.1", '
            '"lifecycle_status": "SUPPORTED", '
            '"eol_date": "2026-06-30", '
            '"observed_at": "2026-08-01T10:00:00+00:00", '
            '"message": "Synthetic lifecycle observation"}]}'
        ),
        (
            '{"findings": [{"source_record_id": "finding-001", '
            '"affected_asset_key": "repo-borealis-renderer", '
            '"component_name": "fictional-render-exporter", '
            '"component_version": "2.4.1", '
            '"lifecycle_status": "END_OF_LIFE", '
            '"eol_date": "2026-13-30", '
            '"observed_at": "2026-08-01T10:00:00", '
            '"message": "Synthetic lifecycle observation"}]}'
        ),
        (
            '{"findings": [{"source_record_id": "finding-001", '
            '"affected_asset_key": "repo-borealis-renderer", '
            '"component_name": "fictional-render-exporter", '
            '"component_version": "2.4.1", '
            '"lifecycle_status": "END_OF_LIFE", '
            '"eol_date": "2026-06-30", '
            '"observed_at": "2026-08-01T10:00:00", '
            '"message": "Synthetic lifecycle observation"}]}'
        ),
    ],
)
def test_malformed_dependency_lifecycle_source_fails_explicitly(
    source_text: str,
) -> None:
    with pytest.raises(DependencyLifecycleSourceFormatError):
        parse_dependency_lifecycle_json(source_text)
