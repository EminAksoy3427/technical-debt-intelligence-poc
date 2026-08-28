import ast
import json
import re
from pathlib import Path
from typing import Any

from app.domain.synthetic_enterprise_estate import (
    SYNTHETIC_ENTERPRISE_ASSETS,
    SYNTHETIC_INCIDENTS,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_APP_ROOT = PROJECT_ROOT / "backend" / "app"
ALEMBIC_ROOT = PROJECT_ROOT / "backend" / "alembic"
CONTROLLED_REPOSITORY_ROOT = PROJECT_ROOT / "synthetic_repositories"
GROUND_TRUTH_ROOT = PROJECT_ROOT / "evaluation" / "ground_truth"
GROUND_TRUTH_PATH = GROUND_TRUTH_ROOT / "correlation_cases.json"
RUNTIME_SEED_PATH = (
    BACKEND_APP_ROOT / "infrastructure" / "database" / "enterprise_estate_seed.py"
)

CASE_FIELDS = {
    "case_key",
    "expected_candidate_group_key",
    "expected_asset_key",
    "issue_family",
    "source_refs",
}
EXPECTED_CASES = {
    "HARDCODED_ENDPOINT": (
        "asteria-hardcoded-endpoint",
        "eval-group-asteria-hardcoded-endpoint",
        "repo-asteria-editor",
    ),
    "MISSING_TIMEOUT": (
        "borealis-missing-timeout",
        "eval-group-borealis-missing-timeout",
        "repo-borealis-renderer",
    ),
    "PROCESS_LOCAL_STATE": (
        "orbit-process-local-state",
        "eval-group-orbit-process-local-state",
        "repo-orbit-catalog",
    ),
    "RECURRING_INCIDENT_PATTERN": (
        "orbit-recurring-incidents",
        "eval-group-orbit-recurring-incidents",
        "svc-orbit-catalog",
    ),
}
EXPECTED_CONTROLLED_SOURCES = {
    "HARDCODED_ENDPOINT": ("repo-asteria-editor", "catalog_client.py"),
    "MISSING_TIMEOUT": ("repo-borealis-renderer", "renderer_client.py"),
    "PROCESS_LOCAL_STATE": ("repo-orbit-catalog", "catalog_cache.py"),
}
EXPECTED_ORBIT_INCIDENT_KEYS = {
    "inc-orbit-001",
    "inc-orbit-002",
    "inc-orbit-003",
}
GROUP_KEY_PATTERN = re.compile(r"^eval-group-[a-z0-9]+(?:-[a-z0-9]+)*$")
FORBIDDEN_ANSWER_FIELDS = {
    "agent_classification",
    "agent_recommendation",
    "candidate",
    "candidate_id",
    "closure_expectation",
    "effort_score",
    "evidence_id",
    "human_validation_result",
    "management_action",
    "owner_decision",
    "paid_decision",
    "remediation_recommendation",
    "risk_score",
    "signal_id",
    "target_date",
    "technical_debt",
    "technical_debt_id",
    "technical_debt_status",
}


def _load_ground_truth() -> dict[str, Any]:
    return json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))


def _cases_by_issue_family() -> dict[str, dict[str, Any]]:
    return {
        case["issue_family"]: case
        for case in _load_ground_truth()["cases"]
    }


def _all_object_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key
            for child in value.values()
            for key in _all_object_keys(child)
        }
    if isinstance(value, list):
        return {
            key
            for child in value
            for key in _all_object_keys(child)
        }
    return set()


def _imported_module_names(source_file: Path) -> set[str]:
    source_tree = ast.parse(
        source_file.read_text(encoding="utf-8"),
        filename=str(source_file),
    )
    imported_modules = set()
    for node in ast.walk(source_tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module)
    return imported_modules


def test_ground_truth_document_has_the_expected_minimal_contract() -> None:
    ground_truth = _load_ground_truth()

    assert set(ground_truth) == {"schema_version", "cases"}
    assert ground_truth["schema_version"] == 1
    assert len(ground_truth["cases"]) == 4
    assert all(set(case) == CASE_FIELDS for case in ground_truth["cases"])

    case_keys = [case["case_key"] for case in ground_truth["cases"]]
    group_keys = [
        case["expected_candidate_group_key"] for case in ground_truth["cases"]
    ]

    assert len(case_keys) == len(set(case_keys))
    assert len(group_keys) == len(set(group_keys))
    assert all(GROUP_KEY_PATTERN.fullmatch(group_key) for group_key in group_keys)


def test_ground_truth_cases_match_the_controlled_synthetic_facts() -> None:
    cases = _cases_by_issue_family()

    assert set(cases) == set(EXPECTED_CASES)
    for issue_family, (case_key, group_key, asset_key) in EXPECTED_CASES.items():
        case = cases[issue_family]
        assert (
            case["case_key"],
            case["expected_candidate_group_key"],
            case["expected_asset_key"],
        ) == (case_key, group_key, asset_key)

    asset_keys = {asset.asset_key for asset in SYNTHETIC_ENTERPRISE_ASSETS}
    assert {case["expected_asset_key"] for case in cases.values()} <= asset_keys


def test_controlled_repository_source_references_resolve() -> None:
    cases = _cases_by_issue_family()

    for issue_family, expected_source in EXPECTED_CONTROLLED_SOURCES.items():
        source_refs = cases[issue_family]["source_refs"]
        assert len(source_refs) == 1

        source_ref = source_refs[0]
        assert set(source_ref) == {
            "source_type",
            "repository_key",
            "source_file",
        }
        assert source_ref["source_type"] == "CONTROLLED_REPOSITORY"
        assert (
            source_ref["repository_key"],
            source_ref["source_file"],
        ) == expected_source

        source_file = (
            CONTROLLED_REPOSITORY_ROOT
            / source_ref["repository_key"]
            / source_ref["source_file"]
        )
        assert source_file.is_file()
        assert source_file.parent == (
            CONTROLLED_REPOSITORY_ROOT / source_ref["repository_key"]
        )


def test_orbit_incident_references_resolve_to_one_distinct_group() -> None:
    cases = _cases_by_issue_family()
    incident_case = cases["RECURRING_INCIDENT_PATTERN"]
    process_state_case = cases["PROCESS_LOCAL_STATE"]
    source_refs = incident_case["source_refs"]

    assert all(
        set(source_ref) == {"source_type", "incident_key"}
        and source_ref["source_type"] == "INCIDENT"
        for source_ref in source_refs
    )
    assert {source_ref["incident_key"] for source_ref in source_refs} == (
        EXPECTED_ORBIT_INCIDENT_KEYS
    )

    known_incident_keys = {
        incident.incident_key for incident in SYNTHETIC_INCIDENTS
    }
    assert EXPECTED_ORBIT_INCIDENT_KEYS <= known_incident_keys
    assert incident_case["expected_candidate_group_key"] != (
        process_state_case["expected_candidate_group_key"]
    )


def test_ground_truth_contains_no_runtime_ids_or_premature_answers() -> None:
    ground_truth = _load_ground_truth()
    object_keys = _all_object_keys(ground_truth)

    assert not {key for key in object_keys if key == "id" or key.endswith("_id")}
    assert object_keys.isdisjoint(FORBIDDEN_ANSWER_FIELDS)


def test_ground_truth_is_outside_runtime() -> None:
    assert GROUND_TRUTH_PATH.is_file()
    assert GROUND_TRUTH_PATH.is_relative_to(PROJECT_ROOT)
    assert not GROUND_TRUTH_PATH.is_relative_to(BACKEND_APP_ROOT)


def test_runtime_modules_do_not_import_or_load_ground_truth() -> None:
    for source_file in BACKEND_APP_ROOT.rglob("*.py"):
        imported_modules = _imported_module_names(source_file)
        assert all(
            not module.startswith("evaluation")
            and "ground_truth" not in module
            for module in imported_modules
        )

        source_text = source_file.read_text(encoding="utf-8").lower()
        assert "ground_truth" not in source_text
        assert "correlation_cases.json" not in source_text
        assert "evaluation/ground_truth" not in source_text.replace("\\", "/")


def test_ground_truth_is_absent_from_database_schema_and_runtime_seed() -> None:
    table_names = set(EnterpriseAssetModel.metadata.tables)
    assert all(
        "ground_truth" not in table_name and "evaluation" not in table_name
        for table_name in table_names
    )

    for migration_file in ALEMBIC_ROOT.rglob("*.py"):
        migration_text = migration_file.read_text(encoding="utf-8").lower()
        assert "ground_truth" not in migration_text
        assert "correlation_cases.json" not in migration_text

    seed_text = RUNTIME_SEED_PATH.read_text(encoding="utf-8").lower()
    assert "ground_truth" not in seed_text
    assert "correlation_cases.json" not in seed_text
    assert "evaluation" not in seed_text
