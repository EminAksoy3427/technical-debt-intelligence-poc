from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.domain.action_verifications import (
    ActionVerification,
    ActionVerificationReasonCode,
    ActionVerificationResult,
)

CREATED_AT = datetime(2026, 9, 7, 21, 0, tzinfo=UTC)
VERIFICATION_ID = UUID("60000000-0000-0000-0000-000000000001")
EXECUTION_ID = UUID("70000000-0000-0000-0000-000000000001")


def test_pass_requires_observed_issue_and_no_reason() -> None:
    verification = ActionVerification(
        action_verification_id=VERIFICATION_ID,
        action_execution_id=EXECUTION_ID,
        result=ActionVerificationResult.PASS,
        observed_issue_number=7,
        observed_issue_url="https://github.com/demo-owner/demo-repository/issues/7",
        safe_reason_code=None,
        created_at=CREATED_AT,
    )

    assert verification.result is ActionVerificationResult.PASS
    with pytest.raises(ValueError, match="cannot have a reason"):
        ActionVerification(
            action_verification_id=VERIFICATION_ID,
            action_execution_id=EXECUTION_ID,
            result=ActionVerificationResult.PASS,
            observed_issue_number=7,
            observed_issue_url="https://github.com/demo-owner/demo-repository/issues/7",
            safe_reason_code=ActionVerificationReasonCode.TITLE_MISMATCH,
            created_at=CREATED_AT,
        )


def test_unavailable_cannot_claim_an_issue_or_close_execution() -> None:
    verification = ActionVerification(
        action_verification_id=VERIFICATION_ID,
        action_execution_id=EXECUTION_ID,
        result=ActionVerificationResult.UNAVAILABLE,
        observed_issue_number=None,
        observed_issue_url=None,
        safe_reason_code=ActionVerificationReasonCode.TRANSPORT_UNAVAILABLE,
        created_at=CREATED_AT,
    )

    assert verification.result is ActionVerificationResult.UNAVAILABLE
    with pytest.raises(ValueError, match="cannot claim an observed issue"):
        ActionVerification(
            action_verification_id=VERIFICATION_ID,
            action_execution_id=EXECUTION_ID,
            result=ActionVerificationResult.UNAVAILABLE,
            observed_issue_number=7,
            observed_issue_url="https://github.com/example/issues/7",
            safe_reason_code=ActionVerificationReasonCode.TRANSPORT_UNAVAILABLE,
            created_at=CREATED_AT,
        )


def test_fail_requires_a_mismatch_reason() -> None:
    with pytest.raises(ValueError, match="mismatch reason"):
        ActionVerification(
            action_verification_id=VERIFICATION_ID,
            action_execution_id=EXECUTION_ID,
            result=ActionVerificationResult.FAIL,
            observed_issue_number=None,
            observed_issue_url=None,
            safe_reason_code=None,
            created_at=CREATED_AT,
        )
