from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.candidate_enterprise_context import CandidateEnterpriseContext
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationshipType,
    AssetType,
    IncidentSeverity,
    OwnershipRole,
)
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_read_model import (
    CandidateDetail,
    CandidateSummary,
)


class CanonicalAssetResponse(BaseModel):
    asset_key: str
    asset_type: AssetType


class EnterpriseAssetResponse(CanonicalAssetResponse):
    name: str
    criticality: AssetCriticality
    lifecycle_status: AssetLifecycleStatus


class CandidateResponse(BaseModel):
    candidate_id: UUID
    signal_ids: list[UUID]
    evidence_ids: list[UUID]
    canonical_asset: CanonicalAssetResponse
    hypothesis: str
    correlation_rationale: str


class SignalResponse(BaseModel):
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: datetime
    signal_type: str
    affected_asset: CanonicalAssetResponse
    severity: str | None
    evidence_ids: list[UUID]


class EvidenceResponse(BaseModel):
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: datetime
    reference_uri: str | None


class AssetOwnershipResponse(BaseModel):
    asset_key: str
    team_key: str
    ownership_role: OwnershipRole


class TeamResponse(BaseModel):
    team_key: str
    name: str


class EnterpriseAssetOwnershipResponse(BaseModel):
    asset_ownership: AssetOwnershipResponse
    team: TeamResponse


class AssetRelationshipResponse(BaseModel):
    source_asset_key: str
    target_asset_key: str
    relationship_type: AssetRelationshipType


class IncidentResponse(BaseModel):
    incident_key: str
    primary_affected_asset_key: str
    severity: IncidentSeverity
    title: str
    started_at: datetime
    resolved_at: datetime | None


class CandidateEnterpriseContextResponse(BaseModel):
    candidate_id: UUID
    enterprise_asset: EnterpriseAssetResponse
    enterprise_ownerships: list[EnterpriseAssetOwnershipResponse]
    direct_relationships: list[AssetRelationshipResponse]
    direct_incidents: list[IncidentResponse]


class CandidateDependencyContextResponse(BaseModel):
    """Deterministic dependency reachability facts, not guaranteed impact."""

    candidate_id: UUID
    candidate_asset: CanonicalAssetResponse
    dependency_anchors: list[CanonicalAssetResponse]
    direct_dependencies: list[CanonicalAssetResponse]
    direct_dependents: list[CanonicalAssetResponse]
    reachable_dependents: list[CanonicalAssetResponse] = Field(
        description=(
            "Assets deterministically reachable as dependents in the persisted "
            "dependency graph; this is not guaranteed outage or causal impact."
        )
    )


class CandidateSummaryResponse(BaseModel):
    candidate_id: UUID
    hypothesis: str
    canonical_asset: CanonicalAssetResponse
    enterprise_asset: EnterpriseAssetResponse
    signal_count: int
    evidence_count: int


class CandidateListResponse(BaseModel):
    items: list[CandidateSummaryResponse]
    count: int


class CandidateDetailResponse(BaseModel):
    candidate: CandidateResponse
    signals: list[SignalResponse]
    evidence: list[EvidenceResponse]
    enterprise_context: CandidateEnterpriseContextResponse
    dependency_context: CandidateDependencyContextResponse


def candidate_list_response(
    summaries: tuple[CandidateSummary, ...],
) -> CandidateListResponse:
    items = [
        CandidateSummaryResponse(
            candidate_id=summary.candidate.candidate_id,
            hypothesis=summary.candidate.hypothesis,
            canonical_asset=_canonical_asset_response(
                summary.candidate.canonical_asset
            ),
            enterprise_asset=_enterprise_asset_response(summary.enterprise_context),
            signal_count=len(summary.candidate.signal_ids),
            evidence_count=len(summary.candidate.evidence_ids),
        )
        for summary in summaries
    ]
    return CandidateListResponse(items=items, count=len(items))


def candidate_detail_response(detail: CandidateDetail) -> CandidateDetailResponse:
    return CandidateDetailResponse(
        candidate=_candidate_response(detail.candidate),
        signals=[_signal_response(signal) for signal in detail.signals],
        evidence=[_evidence_response(evidence) for evidence in detail.evidence],
        enterprise_context=_enterprise_context_response(detail.enterprise_context),
        dependency_context=_dependency_context_response(detail.dependency_context),
    )


def _canonical_asset_response(asset: CanonicalAssetRef) -> CanonicalAssetResponse:
    return CanonicalAssetResponse(
        asset_key=asset.asset_key,
        asset_type=asset.asset_type,
    )


def _enterprise_asset_response(
    context: CandidateEnterpriseContext,
) -> EnterpriseAssetResponse:
    asset = context.enterprise_asset
    return EnterpriseAssetResponse(
        asset_key=asset.asset_key,
        asset_type=asset.asset_type,
        name=asset.name,
        criticality=asset.criticality,
        lifecycle_status=asset.lifecycle_status,
    )


def _candidate_response(candidate: Candidate) -> CandidateResponse:
    return CandidateResponse(
        candidate_id=candidate.candidate_id,
        signal_ids=sorted(candidate.signal_ids, key=lambda item: item.hex),
        evidence_ids=sorted(candidate.evidence_ids, key=lambda item: item.hex),
        canonical_asset=_canonical_asset_response(candidate.canonical_asset),
        hypothesis=candidate.hypothesis,
        correlation_rationale=candidate.correlation_rationale,
    )


def _signal_response(signal: Signal) -> SignalResponse:
    return SignalResponse(
        signal_id=signal.signal_id,
        source_system=signal.source_system,
        source_record_id=signal.source_record_id,
        detected_at=signal.detected_at,
        signal_type=signal.signal_type,
        affected_asset=_canonical_asset_response(signal.affected_asset),
        severity=signal.severity,
        evidence_ids=sorted(signal.evidence_ids, key=lambda item: item.hex),
    )


def _evidence_response(evidence: Evidence) -> EvidenceResponse:
    return EvidenceResponse(
        evidence_id=evidence.evidence_id,
        source_system=evidence.source_system,
        source_reference=evidence.source_reference,
        captured_at=evidence.captured_at,
        reference_uri=evidence.reference_uri,
    )


def _enterprise_context_response(
    context: CandidateEnterpriseContext,
) -> CandidateEnterpriseContextResponse:
    return CandidateEnterpriseContextResponse(
        candidate_id=context.candidate_id,
        enterprise_asset=_enterprise_asset_response(context),
        enterprise_ownerships=[
            EnterpriseAssetOwnershipResponse(
                asset_ownership=AssetOwnershipResponse(
                    asset_key=item.asset_ownership.asset_key,
                    team_key=item.asset_ownership.team_key,
                    ownership_role=item.asset_ownership.ownership_role,
                ),
                team=TeamResponse(
                    team_key=item.team.team_key,
                    name=item.team.name,
                ),
            )
            for item in context.enterprise_ownerships
        ],
        direct_relationships=[
            AssetRelationshipResponse(
                source_asset_key=item.source_asset_key,
                target_asset_key=item.target_asset_key,
                relationship_type=item.relationship_type,
            )
            for item in context.direct_relationships
        ],
        direct_incidents=[
            IncidentResponse(
                incident_key=item.incident_key,
                primary_affected_asset_key=item.primary_affected_asset_key,
                severity=item.severity,
                title=item.title,
                started_at=item.started_at,
                resolved_at=item.resolved_at,
            )
            for item in context.direct_incidents
        ],
    )


def _dependency_context_response(
    context: CandidateDependencyContext,
) -> CandidateDependencyContextResponse:
    return CandidateDependencyContextResponse(
        candidate_id=context.candidate_id,
        candidate_asset=_canonical_asset_response(context.candidate_asset),
        dependency_anchors=[
            _canonical_asset_response(item) for item in context.dependency_anchors
        ],
        direct_dependencies=[
            _canonical_asset_response(item) for item in context.direct_dependencies
        ],
        direct_dependents=[
            _canonical_asset_response(item) for item in context.direct_dependents
        ],
        reachable_dependents=[
            _canonical_asset_response(item) for item in context.reachable_dependents
        ],
    )
