from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.base import Base
from app.infrastructure.database.technical_debt_models import TechnicalDebtModel


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


def test_technical_debt_orm_metadata_preserves_provenance_without_planning() -> None:
    table = TechnicalDebtModel.__table__

    assert table.name == "technical_debts"
    assert set(table.columns.keys()) == {
        "technical_debt_id",
        "source_candidate_id",
        "creation_human_decision_id",
        "lifecycle_status",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["technical_debt_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "candidates.candidate_id",
        "human_decisions.human_decision_id",
    }
    assert frozenset({"source_candidate_id"}) in _unique_column_sets("technical_debts")
    assert frozenset({"creation_human_decision_id"}) in _unique_column_sets(
        "technical_debts"
    )
    assert "ck_technical_debts_lifecycle_status" in _check_names("technical_debts")
    assert {
        "hypothesis",
        "risk",
        "effort",
        "owner",
        "priority",
        "target_date",
        "verification",
        "closure",
    }.isdisjoint(table.columns.keys())
    assert (
        "delete"
        not in TechnicalDebtModel.__mapper__.relationships["source_candidate"].cascade
    )
    assert (
        "delete"
        not in TechnicalDebtModel.__mapper__.relationships[
            "creation_human_decision"
        ].cascade
    )
