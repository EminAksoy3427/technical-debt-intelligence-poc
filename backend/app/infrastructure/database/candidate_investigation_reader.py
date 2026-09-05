from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.agent.ports import (
    CandidateDependencyInvestigation,
    CandidateEnterpriseInvestigation,
    CandidateInvestigation,
    CandidateInvestigationAsset,
    CandidateInvestigationEnterpriseAsset,
    CandidateInvestigationEvidence,
    CandidateInvestigationIncident,
    CandidateInvestigationOwnership,
    CandidateInvestigationOwnershipRecord,
    CandidateInvestigationRelationship,
    CandidateInvestigationSignal,
    CandidateInvestigationTeam,
)
from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.candidate_enterprise_context import CandidateEnterpriseContext
from app.infrastructure.database.candidate_dependency_context import (
    load_candidate_dependency_context,
)
from app.infrastructure.database.candidate_enterprise_context import (
    load_candidate_enterprise_context,
)
from app.infrastructure.database.candidate_read_model import load_candidate_detail


@dataclass(frozen=True)
class DatabaseCandidateInvestigationReader:
    """Project existing Candidate reads into the application investigation port."""

    session: Session

    def read_candidate_evidence(
        self,
        candidate_id: UUID,
    ) -> CandidateInvestigation | None:
        detail = load_candidate_detail(self.session, candidate_id)
        if detail is None:
            return None

        candidate = detail.candidate
        return CandidateInvestigation(
            candidate_id=candidate.candidate_id,
            asset_key=candidate.canonical_asset.asset_key,
            asset_type=candidate.canonical_asset.asset_type,
            hypothesis=candidate.hypothesis,
            correlation_rationale=candidate.correlation_rationale,
            signals=tuple(
                CandidateInvestigationSignal(
                    signal_id=signal.signal_id,
                    source_system=signal.source_system,
                    source_record_id=signal.source_record_id,
                    detected_at=signal.detected_at,
                    signal_type=signal.signal_type,
                    severity=signal.severity,
                    evidence_ids=tuple(
                        sorted(signal.evidence_ids, key=lambda item: item.hex)
                    ),
                )
                for signal in detail.signals
            ),
            evidence=tuple(
                CandidateInvestigationEvidence(
                    evidence_id=evidence.evidence_id,
                    source_system=evidence.source_system,
                    source_reference=evidence.source_reference,
                    captured_at=evidence.captured_at,
                    reference_uri=evidence.reference_uri,
                )
                for evidence in detail.evidence
            ),
        )

    def read_candidate_dependency_context(
        self,
        candidate_id: UUID,
    ) -> CandidateDependencyInvestigation | None:
        context = load_candidate_dependency_context(self.session, candidate_id)
        if context is None:
            return None
        return _dependency_investigation(context)

    def read_candidate_enterprise_context(
        self,
        candidate_id: UUID,
    ) -> CandidateEnterpriseInvestigation | None:
        context = load_candidate_enterprise_context(self.session, candidate_id)
        if context is None:
            return None
        return _enterprise_investigation(context)


def _dependency_investigation(
    context: CandidateDependencyContext,
) -> CandidateDependencyInvestigation:
    return CandidateDependencyInvestigation(
        candidate_id=context.candidate_id,
        candidate_asset=_investigation_asset(context.candidate_asset),
        dependency_anchors=tuple(
            _investigation_asset(asset) for asset in context.dependency_anchors
        ),
        direct_dependencies=tuple(
            _investigation_asset(asset) for asset in context.direct_dependencies
        ),
        direct_dependents=tuple(
            _investigation_asset(asset) for asset in context.direct_dependents
        ),
        reachable_dependents=tuple(
            _investigation_asset(asset) for asset in context.reachable_dependents
        ),
    )


def _enterprise_investigation(
    context: CandidateEnterpriseContext,
) -> CandidateEnterpriseInvestigation:
    asset = context.enterprise_asset
    return CandidateEnterpriseInvestigation(
        candidate_id=context.candidate_id,
        enterprise_asset=CandidateInvestigationEnterpriseAsset(
            asset_key=asset.asset_key,
            asset_type=asset.asset_type,
            name=asset.name,
            criticality=asset.criticality,
            lifecycle_status=asset.lifecycle_status,
        ),
        enterprise_ownerships=tuple(
            CandidateInvestigationOwnership(
                asset_ownership=CandidateInvestigationOwnershipRecord(
                    asset_key=item.asset_ownership.asset_key,
                    team_key=item.asset_ownership.team_key,
                    ownership_role=item.asset_ownership.ownership_role,
                ),
                team=CandidateInvestigationTeam(
                    team_key=item.team.team_key,
                    name=item.team.name,
                ),
            )
            for item in context.enterprise_ownerships
        ),
        direct_relationships=tuple(
            CandidateInvestigationRelationship(
                source_asset_key=item.source_asset_key,
                target_asset_key=item.target_asset_key,
                relationship_type=item.relationship_type,
            )
            for item in context.direct_relationships
        ),
        direct_incidents=tuple(
            CandidateInvestigationIncident(
                incident_key=item.incident_key,
                primary_affected_asset_key=item.primary_affected_asset_key,
                severity=item.severity,
                title=item.title,
                started_at=item.started_at,
                resolved_at=item.resolved_at,
            )
            for item in context.direct_incidents
        ),
    )


def _investigation_asset(asset: CanonicalAssetRef) -> CandidateInvestigationAsset:
    return CandidateInvestigationAsset(
        asset_key=asset.asset_key,
        asset_type=asset.asset_type,
    )
