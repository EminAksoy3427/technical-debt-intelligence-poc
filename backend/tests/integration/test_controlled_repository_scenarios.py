import ast
import re
from pathlib import Path

from app.domain.enterprise_estate import AssetType
from app.domain.synthetic_enterprise_estate import SYNTHETIC_ENTERPRISE_ASSETS

CONTROLLED_REPOSITORY_ROOT = (
    Path(__file__).resolve().parents[3] / "synthetic_repositories"
)
EXPECTED_REPOSITORY_KEYS = {
    "repo-asteria-editor",
    "repo-borealis-renderer",
    "repo-orbit-catalog",
}
IPV4_ADDRESS_PATTERN = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _repository_asset_keys() -> set[str]:
    return {
        asset.asset_key
        for asset in SYNTHETIC_ENTERPRISE_ASSETS
        if asset.asset_type is AssetType.REPOSITORY
    }


def _controlled_python_files() -> tuple[Path, ...]:
    return tuple(sorted(CONTROLLED_REPOSITORY_ROOT.glob("*/*.py")))


def _parse_source(source_file: Path) -> ast.Module:
    return ast.parse(source_file.read_text(encoding="utf-8"), filename=str(source_file))


def _network_calls(source_tree: ast.Module) -> list[ast.Call]:
    return [
        node
        for node in ast.walk(source_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "urlopen"
    ]


def _http_string_literals(source_tree: ast.Module) -> tuple[str, ...]:
    return tuple(
        node.value
        for node in ast.walk(source_tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and node.value.startswith(("http://", "https://"))
    )


def test_controlled_repository_directories_match_repository_asset_keys() -> None:
    actual_directories = {
        path.name for path in CONTROLLED_REPOSITORY_ROOT.iterdir() if path.is_dir()
    }

    assert _repository_asset_keys() == EXPECTED_REPOSITORY_KEYS
    assert actual_directories == _repository_asset_keys()


def test_controlled_python_sources_are_valid_and_fictional() -> None:
    source_files = _controlled_python_files()

    assert len(source_files) == 3
    for source_file in source_files:
        source_text = source_file.read_text(encoding="utf-8").lower()

        _parse_source(source_file)
        assert not IPV4_ADDRESS_PATTERN.search(source_text)
        assert "bank" not in source_text
        assert "employee" not in source_text
        assert "system" not in source_text


def test_asteria_editor_has_synthetic_hard_coded_endpoint_with_timeout() -> None:
    source_tree = _parse_source(
        CONTROLLED_REPOSITORY_ROOT / "repo-asteria-editor" / "catalog_client.py"
    )
    network_calls = _network_calls(source_tree)

    assert _http_string_literals(source_tree) == (
        "https://catalog.synthetic.invalid/v1/documents",
    )
    assert len(network_calls) == 1
    assert {keyword.arg for keyword in network_calls[0].keywords} >= {"timeout"}


def test_borealis_renderer_has_injected_endpoint_without_timeout() -> None:
    source_tree = _parse_source(
        CONTROLLED_REPOSITORY_ROOT / "repo-borealis-renderer" / "renderer_client.py"
    )
    network_calls = _network_calls(source_tree)

    assert _http_string_literals(source_tree) == ()
    assert len(network_calls) == 1
    assert all(
        keyword.arg != "timeout" for keyword in network_calls[0].keywords
    )


def test_orbit_catalog_has_process_local_mutable_state_without_network_calls() -> None:
    source_tree = _parse_source(
        CONTROLLED_REPOSITORY_ROOT / "repo-orbit-catalog" / "catalog_cache.py"
    )
    module_assignments = [
        statement
        for statement in source_tree.body
        if isinstance(statement, (ast.Assign, ast.AnnAssign))
    ]

    assert any(
        isinstance(statement.value, ast.Dict) for statement in module_assignments
    )
    assert _network_calls(source_tree) == []


def test_controlled_repositories_contain_no_nested_git_directories() -> None:
    nested_git_directories = [
        path for path in CONTROLLED_REPOSITORY_ROOT.rglob(".git") if path.is_dir()
    ]

    assert nested_git_directories == []
