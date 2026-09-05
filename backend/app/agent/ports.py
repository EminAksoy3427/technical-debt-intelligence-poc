from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationshipType,
    AssetType,
    IncidentSeverity,
    OwnershipRole,
)


@dataclass(frozen=True)
class CandidateInvestigationSignal:
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: datetime
    signal_type: str
    severity: str | None
    evidence_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class CandidateInvestigationEvidence:
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: datetime
    reference_uri: str | None


@dataclass(frozen=True)
class CandidateInvestigation:
    candidate_id: UUID
    asset_key: str
    asset_type: AssetType
    hypothesis: str
    correlation_rationale: str
    signals: tuple[CandidateInvestigationSignal, ...]
    evidence: tuple[CandidateInvestigationEvidence, ...]


@dataclass(frozen=True)
class CandidateInvestigationAsset:
    asset_key: str
    asset_type: AssetType


@dataclass(frozen=True)
class CandidateDependencyInvestigation:
    candidate_id: UUID
    candidate_asset: CandidateInvestigationAsset
    dependency_anchors: tuple[CandidateInvestigationAsset, ...]
    direct_dependencies: tuple[CandidateInvestigationAsset, ...]
    direct_dependents: tuple[CandidateInvestigationAsset, ...]
    reachable_dependents: tuple[CandidateInvestigationAsset, ...]


@dataclass(frozen=True)
class CandidateInvestigationEnterpriseAsset:
    asset_key: str
    asset_type: AssetType
    name: str
    criticality: AssetCriticality
    lifecycle_status: AssetLifecycleStatus


@dataclass(frozen=True)
class CandidateInvestigationTeam:
    team_key: str
    name: str


@dataclass(frozen=True)
class CandidateInvestigationOwnershipRecord:
    asset_key: str
    team_key: str
    ownership_role: OwnershipRole


@dataclass(frozen=True)
class CandidateInvestigationOwnership:
    asset_ownership: CandidateInvestigationOwnershipRecord
    team: CandidateInvestigationTeam


@dataclass(frozen=True)
class CandidateInvestigationRelationship:
    source_asset_key: str
    target_asset_key: str
    relationship_type: AssetRelationshipType


@dataclass(frozen=True)
class CandidateInvestigationIncident:
    incident_key: str
    primary_affected_asset_key: str
    severity: IncidentSeverity
    title: str
    started_at: datetime
    resolved_at: datetime | None


@dataclass(frozen=True)
class CandidateEnterpriseInvestigation:
    candidate_id: UUID
    enterprise_asset: CandidateInvestigationEnterpriseAsset
    enterprise_ownerships: tuple[CandidateInvestigationOwnership, ...]
    direct_relationships: tuple[CandidateInvestigationRelationship, ...]
    direct_incidents: tuple[CandidateInvestigationIncident, ...]


class CandidateInvestigationReader(Protocol):
    """Application-owned read capability needed by Candidate Agent Tools."""

    def read_candidate_evidence(
        self,
        candidate_id: UUID,
    ) -> CandidateInvestigation | None: ...

    def read_candidate_dependency_context(
        self,
        candidate_id: UUID,
    ) -> CandidateDependencyInvestigation | None: ...

    def read_candidate_enterprise_context(
        self,
        candidate_id: UUID,
    ) -> CandidateEnterpriseInvestigation | None: ...
