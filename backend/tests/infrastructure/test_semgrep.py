import subprocess
from pathlib import Path

import pytest

from app.infrastructure.semgrep import (
    SemgrepExecutableNotFoundError,
    SemgrepExecutionError,
    SemgrepFinding,
    SemgrepOutputError,
    SemgrepScanError,
    parse_semgrep_json,
    scan_semgrep_repository,
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent
CONTROLLED_REPOSITORY_ROOT = PROJECT_ROOT / "synthetic_repositories"
RULES_PATH = BACKEND_ROOT / "semgrep" / "rules.yml"
EXPECTED_RULE_COUNTS = {
    "repo-asteria-editor": {
        "tdi.python.hardcoded-endpoint": 1,
        "tdi.python.missing-timeout": 0,
        "tdi.python.process-local-state": 0,
    },
    "repo-borealis-renderer": {
        "tdi.python.hardcoded-endpoint": 0,
        "tdi.python.missing-timeout": 1,
        "tdi.python.process-local-state": 0,
    },
    "repo-orbit-catalog": {
        "tdi.python.hardcoded-endpoint": 0,
        "tdi.python.missing-timeout": 0,
        "tdi.python.process-local-state": 1,
    },
}


@pytest.fixture(scope="module")
def controlled_findings() -> dict[str, tuple[SemgrepFinding, ...]]:
    return {
        asset_key: scan_semgrep_repository(
            CONTROLLED_REPOSITORY_ROOT / asset_key,
            RULES_PATH,
        )
        for asset_key in EXPECTED_RULE_COUNTS
    }


def test_semgrep_cli_is_invokable() -> None:
    completed = subprocess.run(
        ["semgrep", "--version"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
        shell=False,
    )

    assert completed.returncode == 0
    assert completed.stdout.strip()


def test_asteria_produces_only_hardcoded_endpoint(
    controlled_findings: dict[str, tuple[SemgrepFinding, ...]],
) -> None:
    assert [
        finding.rule_id
        for finding in controlled_findings["repo-asteria-editor"]
    ] == ["tdi.python.hardcoded-endpoint"]


def test_borealis_produces_only_missing_timeout(
    controlled_findings: dict[str, tuple[SemgrepFinding, ...]],
) -> None:
    assert [
        finding.rule_id
        for finding in controlled_findings["repo-borealis-renderer"]
    ] == ["tdi.python.missing-timeout"]


def test_orbit_produces_only_process_local_state(
    controlled_findings: dict[str, tuple[SemgrepFinding, ...]],
) -> None:
    assert [
        finding.rule_id for finding in controlled_findings["repo-orbit-catalog"]
    ] == ["tdi.python.process-local-state"]


def test_controlled_repositories_have_no_cross_rule_false_positives(
    controlled_findings: dict[str, tuple[SemgrepFinding, ...]],
) -> None:
    for asset_key, expected_counts in EXPECTED_RULE_COUNTS.items():
        actual_rule_ids = [
            finding.rule_id for finding in controlled_findings[asset_key]
        ]
        assert {
            rule_id: actual_rule_ids.count(rule_id) for rule_id in expected_counts
        } == expected_counts


def test_controlled_finding_paths_are_repository_relative(
    controlled_findings: dict[str, tuple[SemgrepFinding, ...]],
) -> None:
    for findings in controlled_findings.values():
        for finding in findings:
            assert not Path(finding.relative_path).is_absolute()
            assert ":" not in finding.relative_path
            assert "\\" not in finding.relative_path
            assert finding.relative_path in {
                "catalog_client.py",
                "renderer_client.py",
                "catalog_cache.py",
            }


def test_public_semgrep_json_parses_to_source_specific_finding() -> None:
    output = """
    {
      "errors": [],
      "results": [
        {
          "check_id": "tdi.python.missing-timeout",
          "path": "./renderer_client.py",
          "start": {"line": 5, "col": 10, "offset": 100},
          "end": {"line": 5, "col": 52, "offset": 142},
          "extra": {
            "message": "A urllib request is made without an explicit timeout.",
            "severity": "WARNING",
            "metadata": {}
          }
        }
      ]
    }
    """

    assert parse_semgrep_json(output) == (
        SemgrepFinding(
            rule_id="tdi.python.missing-timeout",
            relative_path="renderer_client.py",
            start_line=5,
            start_column=10,
            end_line=5,
            end_column=52,
            message="A urllib request is made without an explicit timeout.",
            severity="WARNING",
        ),
    )


@pytest.mark.parametrize(
    "output",
    [
        "not JSON",
        "[]",
        '{"errors": []}',
        '{"errors": [], "results": [{"check_id": "rule"}]}',
        (
            '{"errors": [], "results": [{"check_id": "rule", '
            '"path": "C:\\\\source\\\\file.py", '
            '"start": {"line": 1, "col": 1}, '
            '"end": {"line": 1, "col": 2}, '
            '"extra": {"message": "message", "severity": "WARNING"}}]}'
        ),
    ],
)
def test_malformed_or_nonportable_semgrep_json_is_rejected(output: str) -> None:
    with pytest.raises(SemgrepOutputError):
        parse_semgrep_json(output)


def test_semgrep_reported_scan_errors_are_not_treated_as_zero_findings() -> None:
    output = """
    {
      "errors": [
        {
          "code": 3,
          "level": "error",
          "type": "ParseError",
          "message": "source could not be parsed"
        }
      ],
      "results": []
    }
    """

    with pytest.raises(SemgrepScanError, match="ParseError"):
        parse_semgrep_json(output)


def test_missing_semgrep_executable_has_an_explicit_boundary_error() -> None:
    with pytest.raises(SemgrepExecutableNotFoundError):
        scan_semgrep_repository(
            CONTROLLED_REPOSITORY_ROOT / "repo-asteria-editor",
            RULES_PATH,
            executable="semgrep-executable-that-does-not-exist",
        )


def test_nonzero_semgrep_exit_has_an_explicit_boundary_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_run(
        *args: object,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=["semgrep"],
            returncode=2,
            stdout='{"errors": [], "results": []}',
            stderr="tool execution failed",
        )

    monkeypatch.setattr("app.infrastructure.semgrep.subprocess.run", failed_run)

    with pytest.raises(SemgrepExecutionError, match="status 2"):
        scan_semgrep_repository(
            CONTROLLED_REPOSITORY_ROOT / "repo-asteria-editor",
            RULES_PATH,
        )
