from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.action_proposal_models import ActionProposalModel
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


def test_action_proposal_orm_is_immutable_preview_without_occupancy() -> None:
    table = ActionProposalModel.__table__

    assert table.name == "action_proposals"
    assert set(table.columns.keys()) == {
        "action_proposal_id",
        "technical_debt_id",
        "action_type",
        "target_repository_owner",
        "target_repository_name",
        "title",
        "body",
        "payload_fingerprint",
        "reconciliation_marker",
        "prepared_by",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["action_proposal_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "technical_debts.technical_debt_id"
    }
    assert frozenset({"reconciliation_marker"}) in _unique_column_sets(
        "action_proposals"
    )
    assert frozenset({"technical_debt_id"}) not in _unique_column_sets(
        "action_proposals"
    )
    assert frozenset({"technical_debt_id", "action_type"}) not in _unique_column_sets(
        "action_proposals"
    )
    assert "ck_action_proposals_action_type" in _check_names("action_proposals")
    assert {
        "status",
        "approved",
        "executed",
        "verified",
        "risk",
        "effort",
        "owner",
        "priority",
    }.isdisjoint(table.columns.keys())
    assert (
        "delete"
        not in ActionProposalModel.__mapper__.relationships["technical_debt"].cascade
    )


def test_technical_debt_schema_is_unchanged_by_action_proposals() -> None:
    table = TechnicalDebtModel.__table__

    assert set(table.columns.keys()) == {
        "technical_debt_id",
        "source_candidate_id",
        "creation_human_decision_id",
        "lifecycle_status",
        "created_at",
    }
    assert "action_proposal_id" not in table.columns.keys()
    assert "status" not in table.columns.keys()
    assert "risk" not in table.columns.keys()
