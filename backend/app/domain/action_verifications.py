from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class ActionVerificationResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNAVAILABLE = "UNAVAILABLE"


class ActionVerificationReasonCode(StrEnum):
    TITLE_MISMATCH = "TITLE_MISMATCH"
    FINGERPRINT_MISMATCH = "FINGERPRINT_MISMATCH"
    MARKER_MISSING = "MARKER_MISSING"
    PULL_REQUEST = "PULL_REQUEST"
    REFERENCE_MISMATCH = "REFERENCE_MISMATCH"
    TRANSPORT_UNAVAILABLE = "TRANSPORT_UNAVAILABLE"


_FAIL_REASON_CODES = frozenset(
    {
        ActionVerificationReasonCode.TITLE_MISMATCH,
        ActionVerificationReasonCode.FINGERPRINT_MISMATCH,
        ActionVerificationReasonCode.MARKER_MISSING,
        ActionVerificationReasonCode.PULL_REQUEST,
        ActionVerificationReasonCode.REFERENCE_MISMATCH,
    }
)


@dataclass(frozen=True)
class ActionVerification:
    """One immutable read-back attempt against a persisted ActionExecution.

    Verification is not execution, approval, or TechnicalDebt closure.
    """

    action_verification_id: UUID
    action_execution_id: UUID
    result: ActionVerificationResult
    observed_issue_number: int | None
    observed_issue_url: str | None
    safe_reason_code: ActionVerificationReasonCode | None
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.result, ActionVerificationResult):
            raise ValueError("ActionVerification result must be supported")
        if self.safe_reason_code is not None and not isinstance(
            self.safe_reason_code,
            ActionVerificationReasonCode,
        ):
            raise ValueError("ActionVerification reason code must be supported")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("ActionVerification created_at must be timezone-aware")
        if self.observed_issue_url is not None and not self.observed_issue_url.strip():
            raise ValueError("ActionVerification issue URL must not be blank")

        if self.result is ActionVerificationResult.PASS:
            if self.safe_reason_code is not None:
                raise ValueError("PASS ActionVerification cannot have a reason code")
            if self.observed_issue_number is None or self.observed_issue_url is None:
                raise ValueError("PASS ActionVerification requires the observed issue")
        elif self.result is ActionVerificationResult.FAIL:
            if self.safe_reason_code not in _FAIL_REASON_CODES:
                raise ValueError("FAIL ActionVerification requires a mismatch reason")
        elif self.result is ActionVerificationResult.UNAVAILABLE:
            if (
                self.safe_reason_code
                is not ActionVerificationReasonCode.TRANSPORT_UNAVAILABLE
            ):
                raise ValueError("UNAVAILABLE requires TRANSPORT_UNAVAILABLE")
            if (
                self.observed_issue_number is not None
                or self.observed_issue_url is not None
            ):
                raise ValueError(
                    "UNAVAILABLE ActionVerification cannot claim an observed issue"
                )
