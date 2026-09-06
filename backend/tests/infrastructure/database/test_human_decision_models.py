from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.base import Base
from app.infrastructure.database.human_decision_models import HumanDecisionModel


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


def test_human_decision_orm_metadata_is_append_only_and_candidate_scoped() -> None:
    table = HumanDecisionModel.__table__

    assert table.name == "human_decisions"
    assert set(table.columns.keys()) == {
        "human_decision_id",
        "candidate_id",
        "sequence_number",
        "decision_type",
        "rationale",
        "requested_information",
        "actor_reference",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["human_decision_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "candidates.candidate_id"
    }
    assert frozenset({"candidate_id", "sequence_number"}) in _unique_column_sets(
        "human_decisions"
    )
    assert {
        "ck_human_decisions_decision_type",
        "ck_human_decisions_sequence_number_positive",
    } <= _check_names("human_decisions")
    assert {
        "resulting_technical_debt_id",
        "technical_debt_id",
        "structured_assessment",
        "risk",
    }.isdisjoint(table.columns.keys())
    candidate_relationship = HumanDecisionModel.__mapper__.relationships["candidate"]
    assert "delete" not in candidate_relationship.cascade
