import ast
import inspect
from pathlib import Path

from app.agent.composition import build_candidate_tool_registry
from app.domain.human_decisions import HumanDecisionType
from app.governance.contracts import HumanActorContext, HumanValidationCommand
from app.governance.human_validation import apply_human_validation

BACKEND_ROOT = Path(__file__).resolve().parents[2]
GOVERNANCE_DIR = BACKEND_ROOT / "app" / "governance"
HUMAN_VALIDATION_TOOL_IDS = frozenset(
    {
        "human_validation",
        "human_decision",
        "validate_candidate",
        "reject_candidate",
        "request_info",
        "request_information",
        "create_technical_debt",
        *{item.lower() for item in HumanDecisionType},
    }
)


class _UnusedInvestigationReader:
    def read_candidate_evidence(self, candidate_id: object) -> None:
        raise AssertionError("Human Validation must not execute Agent tools")

    def read_candidate_dependency_context(self, candidate_id: object) -> None:
        raise AssertionError("Human Validation must not execute Agent tools")

    def read_candidate_enterprise_context(self, candidate_id: object) -> None:
        raise AssertionError("Human Validation must not execute Agent tools")


def test_human_validation_is_not_registered_as_an_agent_tool() -> None:
    registry = build_candidate_tool_registry(
        _UnusedInvestigationReader()  # type: ignore[arg-type]
    )
    tool_ids = {item.descriptor.tool_id for item in registry.list()}

    assert tool_ids.isdisjoint(HUMAN_VALIDATION_TOOL_IDS)
    assert all(
        "human" not in tool_id
        and "validat" not in tool_id
        and "reject" not in tool_id
        and "approv" not in tool_id
        for tool_id in tool_ids
    )


def test_governance_modules_do_not_import_agent_runtime() -> None:
    forbidden_prefixes = (
        "app.agent",
        "app.agent.openai_provider",
        "app.agent.runtime",
        "app.agent.policy",
        "app.agent.registry",
    )
    imported: set[str] = set()
    for path in sorted(GOVERNANCE_DIR.glob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)

    assert not any(
        module == prefix or module.startswith(f"{prefix}.")
        for module in imported
        for prefix in forbidden_prefixes
    )


def test_human_validation_requires_server_owned_actor_context() -> None:
    parameters = inspect.signature(apply_human_validation).parameters

    assert list(parameters)[:3] == ["session", "command", "actor_context"]
    assert parameters["command"].annotation is HumanValidationCommand
    assert parameters["actor_context"].annotation is HumanActorContext
    assert parameters["actor_context"].default is inspect.Parameter.empty
    assert "actor_reference" not in HumanValidationCommand.__dataclass_fields__
    assert "role" not in HumanValidationCommand.__dataclass_fields__
    assert "authorization" not in HumanValidationCommand.__dataclass_fields__


def test_agent_modules_do_not_import_governance_write_service() -> None:
    imported: set[str] = set()
    for path in sorted((BACKEND_ROOT / "app" / "agent").rglob("*.py")):
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imported.add(node.module)
                imported.update(
                    f"{node.module}.{alias.name}" for alias in node.names
                )

    assert "app.governance.human_validation" not in imported
    assert "app.governance.human_validation.apply_human_validation" not in imported
    assert "app.actions.approval" not in imported
    assert "app.actions.execution_policy" not in imported
    assert not any(
        module == "apply_human_validation" or module.endswith(".apply_human_validation")
        for module in imported
    )
    assert not any(
        module == "approve_action_proposal"
        or module.endswith(".approve_action_proposal")
        for module in imported
    )
