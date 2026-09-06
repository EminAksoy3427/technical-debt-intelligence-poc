from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.api.v1.candidate_schemas import CanonicalAssetResponse
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


class TechnicalDebtDetailResponse(TechnicalDebtApiModel):
    technical_debt_id: UUID
    lifecycle_status: TechnicalDebtLifecycleStatus
    created_at: datetime
    source_candidate: TechnicalDebtSourceCandidateResponse
    creation_human_decision: TechnicalDebtCreationDecisionResponse


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
