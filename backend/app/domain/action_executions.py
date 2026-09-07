from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domain.action_proposals import ActionType


class ActionExecutionStatus(StrEnum):
    IN_PROGRESS = "IN_PROGRESS"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


class ActionExecutionErrorCategory(StrEnum):
    EXTERNAL_REJECTED = "EXTERNAL_REJECTED"
    NOT_SENT = "NOT_SENT"
    TRANSPORT_UNKNOWN = "TRANSPORT_UNKNOWN"


@dataclass(frozen=True)
class ActionExecution:
    """One persisted attempt to execute one immutable ActionProposal."""

    action_execution_id: UUID
    action_proposal_id: UUID
    technical_debt_id: UUID
    action_type: ActionType
    creation_policy_decision_id: UUID
    status: ActionExecutionStatus
    external_issue_id: int | None
    external_issue_number: int | None
    external_issue_url: str | None
    safe_error_category: ActionExecutionErrorCategory | None
    started_at: datetime
    completed_at: datetime | None

    def __post_init__(self) -> None:
        if not isinstance(self.action_type, ActionType):
            raise ValueError("ActionExecution action_type must be supported")
        if not isinstance(self.status, ActionExecutionStatus):
            raise ValueError("ActionExecution status must be supported")
        if self.safe_error_category is not None and not isinstance(
            self.safe_error_category,
            ActionExecutionErrorCategory,
        ):
            raise ValueError("ActionExecution error category must be supported")
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            raise ValueError("ActionExecution started_at must be timezone-aware")
        if self.completed_at is not None and (
            self.completed_at.tzinfo is None
            or self.completed_at.utcoffset() is None
        ):
            raise ValueError("ActionExecution completed_at must be timezone-aware")
        if self.status is ActionExecutionStatus.IN_PROGRESS:
            if self.completed_at is not None:
                raise ValueError("IN_PROGRESS ActionExecution cannot be completed")
            if any(
                value is not None
                for value in (
                    self.external_issue_id,
                    self.external_issue_number,
                    self.external_issue_url,
                    self.safe_error_category,
                )
            ):
                raise ValueError("IN_PROGRESS ActionExecution cannot have an outcome")
        elif self.completed_at is None:
            raise ValueError("Terminal ActionExecution requires completed_at")

        if self.status is ActionExecutionStatus.SUCCEEDED:
            if any(
                value is None
                for value in (
                    self.external_issue_id,
                    self.external_issue_number,
                    self.external_issue_url,
                )
            ):
                raise ValueError(
                    "SUCCEEDED ActionExecution requires an issue reference"
                )
            if self.safe_error_category is not None:
                raise ValueError(
                    "SUCCEEDED ActionExecution cannot have an error category"
                )
            if not self.external_issue_url or not self.external_issue_url.strip():
                raise ValueError(
                    "SUCCEEDED ActionExecution issue URL must not be blank"
                )
        elif self.status in {
            ActionExecutionStatus.FAILED,
            ActionExecutionStatus.UNKNOWN,
        }:
            if self.safe_error_category is None:
                raise ValueError(
                    "Unsuccessful ActionExecution requires an error category"
                )
            if any(
                value is not None
                for value in (
                    self.external_issue_id,
                    self.external_issue_number,
                    self.external_issue_url,
                )
            ):
                raise ValueError("Unsuccessful ActionExecution cannot claim an issue")
            if (
                self.status is ActionExecutionStatus.UNKNOWN
                and self.safe_error_category
                is not ActionExecutionErrorCategory.TRANSPORT_UNKNOWN
            ):
                raise ValueError("UNKNOWN requires TRANSPORT_UNKNOWN")
            if (
                self.status is ActionExecutionStatus.FAILED
                and self.safe_error_category
                not in {
                    ActionExecutionErrorCategory.EXTERNAL_REJECTED,
                    ActionExecutionErrorCategory.NOT_SENT,
                }
            ):
                raise ValueError("FAILED requires a definite failure category")
