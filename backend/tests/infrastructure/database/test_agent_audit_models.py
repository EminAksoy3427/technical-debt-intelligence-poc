from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import configure_mappers

from app.infrastructure.database.agent_audit_models import (
    AgentRunModel,
    PolicyDecisionModel,
    ToolExecutionModel,
)
from app.infrastructure.database.base import Base
from app.infrastructure.database.candidate_models import CandidateModel


def _unique_column_sets(table_name: str) -> set[frozenset[str]]:
    table = Base.metadata.tables[table_name]
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def _check_names(table_name: str) -> set[str | None]:
    return {
        constraint.name
        for constraint in Base.metadata.tables[table_name].constraints
        if isinstance(constraint, CheckConstraint)
    }


def test_metadata_contains_the_agent_audit_tables() -> None:
    assert {"agent_runs", "tool_executions", "policy_decisions"} <= set(
        Base.metadata.tables
    )


def test_agent_run_references_candidate_and_has_lookup_index() -> None:
    table = AgentRunModel.__table__
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "candidates.candidate_id"
    }
    assert "ix_agent_runs_candidate_id" in {index.name for index in table.indexes}
    assert "ck_agent_runs_status" in _check_names("agent_runs")


def test_tool_execution_references_run_and_enforces_sequence_and_duration() -> None:
    table = ToolExecutionModel.__table__
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "agent_runs.agent_run_id"
    }
    assert frozenset({"agent_run_id", "sequence_number"}) in _unique_column_sets(
        "tool_executions"
    )
    assert {
        "ck_tool_executions_sequence_number_positive",
        "ck_tool_executions_duration_non_negative",
    } <= _check_names("tool_executions")


def test_policy_decision_is_one_to_zero_or_one_by_primary_foreign_key() -> None:
    table = PolicyDecisionModel.__table__
    assert list(table.primary_key.columns.keys()) == ["tool_execution_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "tool_executions.tool_execution_id"
    }


def test_orm_relationships_reconstruct_the_audit_aggregate_without_cascades() -> None:
    configure_mappers()
    assert "agent_runs" in CandidateModel.__mapper__.relationships
    assert "candidate" in AgentRunModel.__mapper__.relationships
    assert "tool_executions" in AgentRunModel.__mapper__.relationships
    assert "agent_run" in ToolExecutionModel.__mapper__.relationships
    assert "policy_decision" in ToolExecutionModel.__mapper__.relationships
    assert "tool_execution" in PolicyDecisionModel.__mapper__.relationships

    for relationship_name in ("agent_runs",):
        assert "delete" not in CandidateModel.__mapper__.relationships[
            relationship_name
        ].cascade


def test_audit_tables_store_no_raw_provider_or_hidden_reasoning_payloads() -> None:
    prohibited = {
        "raw_input",
        "raw_output",
        "raw_prompt",
        "raw_model_response",
        "chain_of_thought",
        "reasoning",
        "scratchpad",
        "provider_secret",
        "credentials",
    }
    for model in (AgentRunModel, ToolExecutionModel, PolicyDecisionModel):
        assert prohibited.isdisjoint(model.__table__.columns.keys())
