from datetime import UTC, datetime
from inspect import signature
from uuid import UUID

from app.actions.execution_policy import (
    ActionPolicyResult,
    evaluate_action_execution_policy,
    evaluate_persisted_action_execution_policy,
    record_action_execution_policy_decision,
)
from app.domain.action_approvals import ActionApproval
from app.domain.action_policy import ActionPolicyOutcome, ActionPolicyReasonCode
from app.domain.action_proposals import ActionType

CREATED_AT = datetime(2026, 9, 7, 18, 0, tzinfo=UTC)
PROPOSAL_ID = UUID("00000000-0000-0000-0000-000000000501")
APPROVAL_ID = UUID("00000000-0000-0000-0000-000000000601")
FINGERPRINT = "a" * 64
OTHER_FINGERPRINT = "b" * 64
OWNER = "tdi-demo-target"
NAME = "tdi-action-preview"


def _approval(fingerprint: str = FINGERPRINT) -> ActionApproval:
    return ActionApproval(
        action_approval_id=APPROVAL_ID,
        action_proposal_id=PROPOSAL_ID,
        payload_fingerprint=fingerprint,
        actor_reference="poc:local-reviewer",
        created_at=CREATED_AT,
    )


def _evaluate(**overrides: object) -> ActionPolicyResult:
    values: dict[str, object] = {
        "action_type": ActionType.CREATE_GITHUB_ISSUE.value,
        "proposal_fingerprint": FINGERPRINT,
        "target_repository_owner": OWNER,
        "target_repository_name": NAME,
        "approval": _approval(),
        "execution_enabled": True,
        "executor_ready": True,
        "allowed_repository_owner": OWNER,
        "allowed_repository_name": NAME,
    }
    values.update(overrides)
    return evaluate_action_execution_policy(**values)  # type: ignore[arg-type]


def test_no_approval_denies_with_approval_missing() -> None:
    result = _evaluate(approval=None)

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.APPROVAL_MISSING


def test_fingerprint_mismatch_denies() -> None:
    result = _evaluate(approval=_approval(OTHER_FINGERPRINT))

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.FINGERPRINT_MISMATCH


def test_unsupported_action_type_denies_via_controlled_seam() -> None:
    result = _evaluate(action_type="CREATE_PULL_REQUEST")

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.ACTION_TYPE_NOT_ALLOWED


def test_repository_not_allowlisted_denies() -> None:
    result = _evaluate(
        target_repository_owner="other-owner",
        target_repository_name="other-repo",
    )

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.REPOSITORY_NOT_ALLOWLISTED


def test_execution_disabled_denies() -> None:
    result = _evaluate(execution_enabled=False)

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.EXECUTION_DISABLED


def test_executor_unavailable_denies() -> None:
    result = _evaluate(executor_ready=False)

    assert result.decision is ActionPolicyOutcome.DENY
    assert result.reason_code is ActionPolicyReasonCode.EXECUTION_DISABLED


def test_executor_readiness_is_required_at_every_policy_boundary() -> None:
    for policy_function in (
        evaluate_action_execution_policy,
        record_action_execution_policy_decision,
        evaluate_persisted_action_execution_policy,
    ):
        parameter = signature(policy_function).parameters["executor_ready"]
        assert parameter.default is parameter.empty


def test_trusted_conditions_allow() -> None:
    result = _evaluate()

    assert result.decision is ActionPolicyOutcome.ALLOW
    assert result.reason_code is ActionPolicyReasonCode.POLICY_ALLOWED
    assert result.rule_id == "allow"


def test_policy_does_not_accept_client_authority_inputs() -> None:
    parameters = signature(evaluate_action_execution_policy).parameters

    for forbidden in (
        "effect",
        "risk",
        "scope",
        "approved",
        "actor_reference",
        "title",
        "body",
        "repository",
    ):
        assert forbidden not in parameters


def test_execution_disabled_wins_over_missing_approval() -> None:
    result = _evaluate(execution_enabled=False, approval=None)

    assert result.reason_code is ActionPolicyReasonCode.EXECUTION_DISABLED


def test_policy_result_is_not_execution_success() -> None:
    result = _evaluate()

    assert not hasattr(result, "executed")
    assert not hasattr(result, "github_issue")
    assert not hasattr(result, "verification")
