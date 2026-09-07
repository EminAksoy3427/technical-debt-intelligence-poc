from sqlalchemy import CheckConstraint, UniqueConstraint

from app.infrastructure.database.action_approval_models import ActionApprovalModel
from app.infrastructure.database.action_policy_models import ActionPolicyDecisionModel
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


def test_action_approval_orm_is_append_only_without_logical_occupancy_unique() -> None:
    table = ActionApprovalModel.__table__

    assert table.name == "action_approvals"
    assert set(table.columns.keys()) == {
        "action_approval_id",
        "action_proposal_id",
        "payload_fingerprint",
        "actor_reference",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["action_approval_id"]
    assert {foreign_key.target_fullname for foreign_key in table.foreign_keys} == {
        "action_proposals.action_proposal_id"
    }
    assert frozenset({"action_proposal_id"}) in _unique_column_sets("action_approvals")
    assert frozenset({"technical_debt_id", "action_type"}) not in _unique_column_sets(
        "action_approvals"
    )
    assert {
        "approved",
        "status",
        "revoked",
        "rejected",
        "role",
        "risk",
        "title",
        "body",
    }.isdisjoint(table.columns.keys())


def test_action_policy_decision_orm_is_append_only_and_separate_from_agent_policy() -> (
    None
):
    table = ActionPolicyDecisionModel.__table__

    assert table.name == "action_policy_decisions"
    assert table.name != "policy_decisions"
    assert set(table.columns.keys()) == {
        "action_policy_decision_id",
        "action_proposal_id",
        "action_approval_id",
        "decision",
        "rule_id",
        "reason_code",
        "created_at",
    }
    assert list(table.primary_key.columns.keys()) == ["action_policy_decision_id"]
    assert frozenset({"action_proposal_id"}) not in _unique_column_sets(
        "action_policy_decisions"
    )
    assert "ck_action_policy_decisions_decision" in _check_names(
        "action_policy_decisions"
    )
    assert "ck_action_policy_decisions_allow_requires_approval" in _check_names(
        "action_policy_decisions"
    )
    assert table.columns["action_approval_id"].nullable is True


def test_package_4_does_not_alter_proposal_or_technical_debt_schema() -> None:
    assert set(ActionProposalModel.__table__.columns.keys()) == {
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
    assert set(TechnicalDebtModel.__table__.columns.keys()) == {
        "technical_debt_id",
        "source_candidate_id",
        "creation_human_decision_id",
        "lifecycle_status",
        "created_at",
    }
