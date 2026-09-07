from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.action_execution_models import ActionExecutionModel
from app.infrastructure.database.action_verification_models import (
    ActionVerificationModel,
)
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


def test_action_verification_orm_is_append_only() -> None:
    table = ActionVerificationModel.__table__

    assert table.name == "action_verifications"
    assert set(table.columns.keys()) == {
        "action_verification_id",
        "action_execution_id",
        "result",
        "observed_issue_number",
        "observed_issue_url",
        "safe_reason_code",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["action_verification_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "action_executions.action_execution_id"
    }
    assert frozenset({"action_execution_id"}) not in _unique_column_sets(
        "action_verifications"
    )
    assert "ck_action_verifications_result" in _check_names("action_verifications")
    assert {
        "token",
        "authorization",
        "raw_response",
        "comments",
        "reactions",
        "updated_at",
        "github_token",
    }.isdisjoint(table.columns.keys())


def test_package_6_does_not_alter_execution_or_technical_debt_schema() -> None:
    assert "action_verifications" not in ActionExecutionModel.__table__.columns.keys()
    assert {
        "verification",
        "closure",
        "resolved",
        "verified",
    }.isdisjoint(TechnicalDebtModel.__table__.columns.keys())
