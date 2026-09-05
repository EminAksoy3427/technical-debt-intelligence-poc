from typing import Final
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.agent.contracts import (
    CandidateToolInput,
    ToolDescriptor,
    ToolEffect,
    ToolRegistration,
    ToolRisk,
)
from app.agent.ports import (
    CandidateDependencyInvestigation,
    CandidateEnterpriseInvestigation,
    CandidateInvestigationAsset,
    CandidateInvestigationReader,
)
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetRelationshipType,
    AssetType,
    IncidentSeverity,
    OwnershipRole,
)


class ReadCandidateEvidenceInput(CandidateToolInput):
    candidate_id: UUID


class _ImmutableToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class CandidateAssetResult(_ImmutableToolResult):
    asset_key: str
    asset_type: AssetType


class CandidateSignalResult(_ImmutableToolResult):
    signal_id: UUID
    source_system: str
    source_record_id: str
    detected_at: AwareDatetime
    signal_type: str
    severity: str | None
    evidence_ids: tuple[UUID, ...]


class CandidateEvidenceResult(_ImmutableToolResult):
    evidence_id: UUID
    source_system: str
    source_reference: str
    captured_at: AwareDatetime
    reference_uri: str | None


class ReadCandidateEvidenceResult(_ImmutableToolResult):
    candidate_id: UUID
    canonical_asset: CandidateAssetResult
    hypothesis: str
    correlation_rationale: str
    signals: tuple[CandidateSignalResult, ...]
    evidence: tuple[CandidateEvidenceResult, ...]


class ReadCandidateDependencyContextInput(CandidateToolInput):
    candidate_id: UUID


class ReadCandidateDependencyContextResult(_ImmutableToolResult):
    candidate_id: UUID
    candidate_asset: CandidateAssetResult
    dependency_anchors: tuple[CandidateAssetResult, ...]
    direct_dependencies: tuple[CandidateAssetResult, ...]
    direct_dependents: tuple[CandidateAssetResult, ...]
    reachable_dependents: tuple[CandidateAssetResult, ...] = Field(
        description=(
            "Services deterministically reachable as dependents in the persisted "
            "dependency graph; this is not guaranteed outage or causal impact."
        )
    )


class ReadCandidateEnterpriseContextInput(CandidateToolInput):
    candidate_id: UUID


class CandidateEnterpriseAssetResult(_ImmutableToolResult):
    asset_key: str
    asset_type: AssetType
    name: str
    criticality: AssetCriticality
    lifecycle_status: AssetLifecycleStatus


class CandidateTeamResult(_ImmutableToolResult):
    team_key: str
    name: str


class CandidateOwnershipRecordResult(_ImmutableToolResult):
    asset_key: str
    team_key: str
    ownership_role: OwnershipRole


class CandidateEnterpriseOwnershipResult(_ImmutableToolResult):
    asset_ownership: CandidateOwnershipRecordResult
    team: CandidateTeamResult


class CandidateRelationshipResult(_ImmutableToolResult):
    source_asset_key: str
    target_asset_key: str
    relationship_type: AssetRelationshipType


class CandidateIncidentResult(_ImmutableToolResult):
    incident_key: str
    primary_affected_asset_key: str
    severity: IncidentSeverity
    title: str
    started_at: AwareDatetime
    resolved_at: AwareDatetime | None


class ReadCandidateEnterpriseContextResult(_ImmutableToolResult):
    candidate_id: UUID
    enterprise_asset: CandidateEnterpriseAssetResult
    enterprise_ownerships: tuple[CandidateEnterpriseOwnershipResult, ...]
    direct_relationships: tuple[CandidateRelationshipResult, ...]
    direct_incidents: tuple[CandidateIncidentResult, ...]


class CandidateEvidenceNotFoundError(LookupError):
    """The requested Candidate has no investigation read model."""


class CandidateDependencyContextNotFoundError(LookupError):
    """The requested Candidate has no dependency context read model."""


class CandidateEnterpriseContextNotFoundError(LookupError):
    """The requested Candidate has no enterprise context read model."""


READ_CANDIDATE_EVIDENCE_DESCRIPTOR: Final = ToolDescriptor(
    tool_id="read_candidate_evidence",
    version="1.0.0",
    description="Read grounded Signal and Evidence facts for one Candidate.",
    effect=ToolEffect.READ,
    risk=ToolRisk.LOW,
    required_scopes=frozenset({"candidate:read"}),
)


def create_read_candidate_evidence_registration(
    reader: CandidateInvestigationReader,
) -> ToolRegistration[ReadCandidateEvidenceInput, ReadCandidateEvidenceResult]:
    def read_candidate_evidence(
        tool_input: ReadCandidateEvidenceInput,
    ) -> ReadCandidateEvidenceResult:
        investigation = reader.read_candidate_evidence(tool_input.candidate_id)
        if investigation is None:
            raise CandidateEvidenceNotFoundError(
                f"Candidate not found: {tool_input.candidate_id}"
            )

        return ReadCandidateEvidenceResult(
            candidate_id=investigation.candidate_id,
            canonical_asset=CandidateAssetResult(
                asset_key=investigation.asset_key,
                asset_type=investigation.asset_type,
            ),
            hypothesis=investigation.hypothesis,
            correlation_rationale=investigation.correlation_rationale,
            signals=tuple(
                CandidateSignalResult(
                    signal_id=signal.signal_id,
                    source_system=signal.source_system,
                    source_record_id=signal.source_record_id,
                    detected_at=signal.detected_at,
                    signal_type=signal.signal_type,
                    severity=signal.severity,
                    evidence_ids=signal.evidence_ids,
                )
                for signal in investigation.signals
            ),
            evidence=tuple(
                CandidateEvidenceResult(
                    evidence_id=evidence.evidence_id,
                    source_system=evidence.source_system,
                    source_reference=evidence.source_reference,
                    captured_at=evidence.captured_at,
                    reference_uri=evidence.reference_uri,
                )
                for evidence in investigation.evidence
            ),
        )

    return ToolRegistration(
        descriptor=READ_CANDIDATE_EVIDENCE_DESCRIPTOR,
        input_model=ReadCandidateEvidenceInput,
        result_model=ReadCandidateEvidenceResult,
        executor=read_candidate_evidence,
    )


READ_CANDIDATE_DEPENDENCY_CONTEXT_DESCRIPTOR: Final = ToolDescriptor(
    tool_id="read_candidate_dependency_context",
    version="1.0.0",
    description="Read bounded dependency reachability facts for one Candidate.",
    effect=ToolEffect.READ,
    risk=ToolRisk.LOW,
    required_scopes=frozenset({"candidate:read"}),
)


READ_CANDIDATE_ENTERPRISE_CONTEXT_DESCRIPTOR: Final = ToolDescriptor(
    tool_id="read_candidate_enterprise_context",
    version="1.0.0",
    description="Read recorded enterprise and incident facts for one Candidate.",
    effect=ToolEffect.READ,
    risk=ToolRisk.LOW,
    required_scopes=frozenset({"candidate:read"}),
)


def create_read_candidate_dependency_context_registration(
    reader: CandidateInvestigationReader,
) -> ToolRegistration[
    ReadCandidateDependencyContextInput,
    ReadCandidateDependencyContextResult,
]:
    def read_candidate_dependency_context(
        tool_input: ReadCandidateDependencyContextInput,
    ) -> ReadCandidateDependencyContextResult:
        investigation = reader.read_candidate_dependency_context(
            tool_input.candidate_id
        )
        if investigation is None:
            raise CandidateDependencyContextNotFoundError(
                f"Candidate not found: {tool_input.candidate_id}"
            )
        return _dependency_result(investigation)

    return ToolRegistration(
        descriptor=READ_CANDIDATE_DEPENDENCY_CONTEXT_DESCRIPTOR,
        input_model=ReadCandidateDependencyContextInput,
        result_model=ReadCandidateDependencyContextResult,
        executor=read_candidate_dependency_context,
    )


def create_read_candidate_enterprise_context_registration(
    reader: CandidateInvestigationReader,
) -> ToolRegistration[
    ReadCandidateEnterpriseContextInput,
    ReadCandidateEnterpriseContextResult,
]:
    def read_candidate_enterprise_context(
        tool_input: ReadCandidateEnterpriseContextInput,
    ) -> ReadCandidateEnterpriseContextResult:
        investigation = reader.read_candidate_enterprise_context(
            tool_input.candidate_id
        )
        if investigation is None:
            raise CandidateEnterpriseContextNotFoundError(
                f"Candidate not found: {tool_input.candidate_id}"
            )
        return _enterprise_result(investigation)

    return ToolRegistration(
        descriptor=READ_CANDIDATE_ENTERPRISE_CONTEXT_DESCRIPTOR,
        input_model=ReadCandidateEnterpriseContextInput,
        result_model=ReadCandidateEnterpriseContextResult,
        executor=read_candidate_enterprise_context,
    )


def _dependency_result(
    investigation: CandidateDependencyInvestigation,
) -> ReadCandidateDependencyContextResult:
    return ReadCandidateDependencyContextResult(
        candidate_id=investigation.candidate_id,
        candidate_asset=_asset_result(investigation.candidate_asset),
        dependency_anchors=tuple(
            _asset_result(asset) for asset in investigation.dependency_anchors
        ),
        direct_dependencies=tuple(
            _asset_result(asset) for asset in investigation.direct_dependencies
        ),
        direct_dependents=tuple(
            _asset_result(asset) for asset in investigation.direct_dependents
        ),
        reachable_dependents=tuple(
            _asset_result(asset) for asset in investigation.reachable_dependents
        ),
    )


def _enterprise_result(
    investigation: CandidateEnterpriseInvestigation,
) -> ReadCandidateEnterpriseContextResult:
    asset = investigation.enterprise_asset
    return ReadCandidateEnterpriseContextResult(
        candidate_id=investigation.candidate_id,
        enterprise_asset=CandidateEnterpriseAssetResult(
            asset_key=asset.asset_key,
            asset_type=asset.asset_type,
            name=asset.name,
            criticality=asset.criticality,
            lifecycle_status=asset.lifecycle_status,
        ),
        enterprise_ownerships=tuple(
            CandidateEnterpriseOwnershipResult(
                asset_ownership=CandidateOwnershipRecordResult(
                    asset_key=item.asset_ownership.asset_key,
                    team_key=item.asset_ownership.team_key,
                    ownership_role=item.asset_ownership.ownership_role,
                ),
                team=CandidateTeamResult(
                    team_key=item.team.team_key,
                    name=item.team.name,
                ),
            )
            for item in investigation.enterprise_ownerships
        ),
        direct_relationships=tuple(
            CandidateRelationshipResult(
                source_asset_key=item.source_asset_key,
                target_asset_key=item.target_asset_key,
                relationship_type=item.relationship_type,
            )
            for item in investigation.direct_relationships
        ),
        direct_incidents=tuple(
            CandidateIncidentResult(
                incident_key=item.incident_key,
                primary_affected_asset_key=item.primary_affected_asset_key,
                severity=item.severity,
                title=item.title,
                started_at=item.started_at,
                resolved_at=item.resolved_at,
            )
            for item in investigation.direct_incidents
        ),
    )


def _asset_result(asset: CandidateInvestigationAsset) -> CandidateAssetResult:
    return CandidateAssetResult(
        asset_key=asset.asset_key,
        asset_type=asset.asset_type,
    )
