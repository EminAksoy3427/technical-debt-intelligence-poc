from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.api.v1.candidate_schemas import CanonicalAssetResponse
from app.domain.action_approvals import ActionApproval
from app.domain.action_executions import (
    ActionExecution,
    ActionExecutionErrorCategory,
    ActionExecutionStatus,
)
from app.domain.action_proposals import ActionProposal, ActionType
from app.domain.action_policy import (
    ActionPolicyDecision,
    ActionPolicyOutcome,
    ActionPolicyReasonCode,
)
from app.domain.action_verifications import (
    ActionVerification,
    ActionVerificationReasonCode,
    ActionVerificationResult,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebtLifecycleStatus
from app.infrastructure.database.technical_debt_read_model import (
    TechnicalDebtDetail,
    TechnicalDebtSummary,
)


class TechnicalDebtApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TechnicalDebtListItemResponse(TechnicalDebtApiModel):
    technical_debt_id: UUID
    lifecycle_status: TechnicalDebtLifecycleStatus
    created_at: datetime
    source_candidate_id: UUID
    hypothesis: str
    canonical_asset: CanonicalAssetResponse


class TechnicalDebtListResponse(TechnicalDebtApiModel):
    items: list[TechnicalDebtListItemResponse]
    count: int


class TechnicalDebtSourceCandidateResponse(TechnicalDebtApiModel):
    candidate_id: UUID
    hypothesis: str
    correlation_rationale: str
    canonical_asset: CanonicalAssetResponse


class TechnicalDebtCreationDecisionResponse(TechnicalDebtApiModel):
    human_decision_id: UUID
    decision: HumanDecisionType
    sequence_number: int
    rationale: str | None
    actor_reference: str
    created_at: datetime


class ActionProposalResponse(TechnicalDebtApiModel):
    action_proposal_id: UUID
    technical_debt_id: UUID
    action_type: ActionType
    target_repository_owner: str
    target_repository_name: str
    title: str
    body: str
    payload_fingerprint: str
    reconciliation_marker: str
    prepared_by: str
    created_at: datetime


class ApproveActionProposalRequest(TechnicalDebtApiModel):
    """Untrusted L4 approval intent. Actor identity is server-owned."""

    expected_payload_fingerprint: str = Field(
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    )


class ActionApprovalResponse(TechnicalDebtApiModel):
    action_approval_id: UUID
    action_proposal_id: UUID
    payload_fingerprint: str
    actor_reference: str
    created_at: datetime


class ActionPolicyDecisionResponse(TechnicalDebtApiModel):
    action_policy_decision_id: UUID
    action_proposal_id: UUID
    action_approval_id: UUID | None
    decision: ActionPolicyOutcome
    rule_id: str
    reason_code: ActionPolicyReasonCode
    created_at: datetime


class ActionExecutionResponse(TechnicalDebtApiModel):
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


class ActionVerificationResponse(TechnicalDebtApiModel):
    action_verification_id: UUID
    action_execution_id: UUID
    result: ActionVerificationResult
    observed_issue_number: int | None
    observed_issue_url: str | None
    safe_reason_code: ActionVerificationReasonCode | None
    created_at: datetime


class TechnicalDebtDetailResponse(TechnicalDebtApiModel):
    technical_debt_id: UUID
    lifecycle_status: TechnicalDebtLifecycleStatus
    created_at: datetime
    source_candidate: TechnicalDebtSourceCandidateResponse
    creation_human_decision: TechnicalDebtCreationDecisionResponse
    action_proposals: list[ActionProposalResponse]
    action_approvals: list[ActionApprovalResponse]
    action_policy_decisions: list[ActionPolicyDecisionResponse]
    action_executions: list[ActionExecutionResponse]
    action_verifications: list[ActionVerificationResponse]


def technical_debt_list_response(
    summaries: tuple[TechnicalDebtSummary, ...],
) -> TechnicalDebtListResponse:
    items = [
        TechnicalDebtListItemResponse(
            technical_debt_id=summary.technical_debt.technical_debt_id,
            lifecycle_status=summary.technical_debt.lifecycle_status,
            created_at=summary.technical_debt.created_at,
            source_candidate_id=summary.technical_debt.source_candidate_id,
            hypothesis=summary.source_candidate.hypothesis,
            canonical_asset=_canonical_asset_response(
                summary.source_candidate.canonical_asset
            ),
        )
        for summary in summaries
    ]
    return TechnicalDebtListResponse(items=items, count=len(items))


def technical_debt_detail_response(
    detail: TechnicalDebtDetail,
) -> TechnicalDebtDetailResponse:
    technical_debt = detail.technical_debt
    return TechnicalDebtDetailResponse(
        technical_debt_id=technical_debt.technical_debt_id,
        lifecycle_status=technical_debt.lifecycle_status,
        created_at=technical_debt.created_at,
        source_candidate=_source_candidate_response(detail.source_candidate),
        creation_human_decision=_creation_decision_response(
            detail.creation_human_decision
        ),
        action_proposals=[
            action_proposal_response(proposal) for proposal in detail.action_proposals
        ],
        action_approvals=[
            action_approval_response(approval) for approval in detail.action_approvals
        ],
        action_policy_decisions=[
            action_policy_decision_response(decision)
            for decision in detail.action_policy_decisions
        ],
        action_executions=[
            action_execution_response(execution)
            for execution in detail.action_executions
        ],
        action_verifications=[
            action_verification_response(verification)
            for verification in detail.action_verifications
        ],
    )


def action_proposal_response(proposal: ActionProposal) -> ActionProposalResponse:
    return ActionProposalResponse(
        action_proposal_id=proposal.action_proposal_id,
        technical_debt_id=proposal.technical_debt_id,
        action_type=proposal.action_type,
        target_repository_owner=proposal.target_repository_owner,
        target_repository_name=proposal.target_repository_name,
        title=proposal.payload.title,
        body=proposal.payload.body,
        payload_fingerprint=proposal.payload_fingerprint,
        reconciliation_marker=proposal.reconciliation_marker,
        prepared_by=proposal.prepared_by,
        created_at=proposal.created_at,
    )


def action_approval_response(approval: ActionApproval) -> ActionApprovalResponse:
    return ActionApprovalResponse(
        action_approval_id=approval.action_approval_id,
        action_proposal_id=approval.action_proposal_id,
        payload_fingerprint=approval.payload_fingerprint,
        actor_reference=approval.actor_reference,
        created_at=approval.created_at,
    )


def action_policy_decision_response(
    decision: ActionPolicyDecision,
) -> ActionPolicyDecisionResponse:
    return ActionPolicyDecisionResponse(
        action_policy_decision_id=decision.action_policy_decision_id,
        action_proposal_id=decision.action_proposal_id,
        action_approval_id=decision.action_approval_id,
        decision=decision.decision,
        rule_id=decision.rule_id,
        reason_code=decision.reason_code,
        created_at=decision.created_at,
    )


def action_execution_response(execution: ActionExecution) -> ActionExecutionResponse:
    return ActionExecutionResponse(
        action_execution_id=execution.action_execution_id,
        action_proposal_id=execution.action_proposal_id,
        technical_debt_id=execution.technical_debt_id,
        action_type=execution.action_type,
        creation_policy_decision_id=execution.creation_policy_decision_id,
        status=execution.status,
        external_issue_id=execution.external_issue_id,
        external_issue_number=execution.external_issue_number,
        external_issue_url=execution.external_issue_url,
        safe_error_category=execution.safe_error_category,
        started_at=execution.started_at,
        completed_at=execution.completed_at,
    )


def action_verification_response(
    verification: ActionVerification,
) -> ActionVerificationResponse:
    return ActionVerificationResponse(
        action_verification_id=verification.action_verification_id,
        action_execution_id=verification.action_execution_id,
        result=verification.result,
        observed_issue_number=verification.observed_issue_number,
        observed_issue_url=verification.observed_issue_url,
        safe_reason_code=verification.safe_reason_code,
        created_at=verification.created_at,
    )


def _canonical_asset_response(asset: CanonicalAssetRef) -> CanonicalAssetResponse:
    return CanonicalAssetResponse(
        asset_key=asset.asset_key,
        asset_type=asset.asset_type,
    )


def _source_candidate_response(
    candidate: Candidate,
) -> TechnicalDebtSourceCandidateResponse:
    return TechnicalDebtSourceCandidateResponse(
        candidate_id=candidate.candidate_id,
        hypothesis=candidate.hypothesis,
        correlation_rationale=candidate.correlation_rationale,
        canonical_asset=_canonical_asset_response(candidate.canonical_asset),
    )


def _creation_decision_response(
    decision: HumanDecision,
) -> TechnicalDebtCreationDecisionResponse:
    return TechnicalDebtCreationDecisionResponse(
        human_decision_id=decision.human_decision_id,
        decision=decision.decision_type,
        sequence_number=decision.sequence_number,
        rationale=decision.rationale,
        actor_reference=decision.actor_reference,
        created_at=decision.created_at,
    )
