import type {
  CandidateDependencyAssetItem,
  CandidateDependencyContextPresentation,
  CandidateDetailPresentation,
  CandidateDirectIncidentItem,
  CandidateDirectRelationshipItem,
  CandidateEnterpriseContextPresentation,
  CandidateEnterpriseOwnershipItem,
} from '../types/candidate'
import type {
  AssetRelationshipResponse,
  CandidateDependencyContextResponse,
  CandidateDetailResponse,
  CandidateEnterpriseContextResponse,
  CanonicalAssetResponse,
  EnterpriseAssetOwnershipResponse,
  EvidenceResponse,
  IncidentResponse,
  SignalResponse,
} from '../types/candidateApi'

export function toCandidateDetailPresentation(
  detail: CandidateDetailResponse,
): CandidateDetailPresentation {
  return {
    candidate: {
      candidateId: detail.candidate.candidate_id,
      hypothesis: detail.candidate.hypothesis,
      canonicalAssetKey: detail.candidate.canonical_asset.asset_key,
      canonicalAssetType: detail.candidate.canonical_asset.asset_type,
      assetDisplayName: detail.enterprise_context.enterprise_asset.name,
      correlationRationale: detail.candidate.correlation_rationale,
    },
    signals: detail.signals.map(toCandidateSignalItem),
    evidence: detail.evidence.map(toCandidateEvidenceItem),
    enterpriseContext: toEnterpriseContextPresentation(detail.enterprise_context),
    dependencyContext: toDependencyContextPresentation(detail.dependency_context),
  }
}

function toCandidateSignalItem(signal: SignalResponse): CandidateDetailPresentation['signals'][number] {
  return {
    signalId: signal.signal_id,
    signalType: signal.signal_type,
    sourceSystem: signal.source_system,
    sourceRecordId: signal.source_record_id,
    affectedAssetKey: signal.affected_asset.asset_key,
    affectedAssetType: signal.affected_asset.asset_type,
    detectedAt: signal.detected_at,
    severity: signal.severity,
  }
}

function toCandidateEvidenceItem(
  evidence: EvidenceResponse,
): CandidateDetailPresentation['evidence'][number] {
  return {
    evidenceId: evidence.evidence_id,
    sourceSystem: evidence.source_system,
    sourceReference: evidence.source_reference,
    capturedAt: evidence.captured_at,
    referenceUri: evidence.reference_uri,
  }
}

function toEnterpriseContextPresentation(
  context: CandidateEnterpriseContextResponse,
): CandidateEnterpriseContextPresentation {
  const asset = context.enterprise_asset
  return {
    asset: {
      name: asset.name,
      assetKey: asset.asset_key,
      assetType: asset.asset_type,
      criticality: asset.criticality,
      lifecycleStatus: asset.lifecycle_status,
    },
    ownerships: context.enterprise_ownerships.map(toEnterpriseOwnershipItem),
    relationships: context.direct_relationships.map(toDirectRelationshipItem),
    incidents: context.direct_incidents.map(toDirectIncidentItem),
  }
}

function toEnterpriseOwnershipItem(
  item: EnterpriseAssetOwnershipResponse,
): CandidateEnterpriseOwnershipItem {
  return {
    teamName: item.team.name,
    teamKey: item.team.team_key,
    ownershipRole: item.asset_ownership.ownership_role,
  }
}

function toDirectRelationshipItem(
  item: AssetRelationshipResponse,
): CandidateDirectRelationshipItem {
  return {
    sourceAssetKey: item.source_asset_key,
    targetAssetKey: item.target_asset_key,
    relationshipType: item.relationship_type,
  }
}

function toDirectIncidentItem(item: IncidentResponse): CandidateDirectIncidentItem {
  return {
    incidentKey: item.incident_key,
    title: item.title,
    severity: item.severity,
    startedAt: item.started_at,
    resolvedAt: item.resolved_at,
    primaryAffectedAssetKey: item.primary_affected_asset_key,
  }
}

function toDependencyContextPresentation(
  context: CandidateDependencyContextResponse,
): CandidateDependencyContextPresentation {
  return {
    candidateAsset: toDependencyAssetItem(context.candidate_asset),
    dependencyAnchors: context.dependency_anchors.map(toDependencyAssetItem),
    directDependencies: context.direct_dependencies.map(toDependencyAssetItem),
    directDependents: context.direct_dependents.map(toDependencyAssetItem),
    reachableDependents: context.reachable_dependents.map(toDependencyAssetItem),
  }
}

function toDependencyAssetItem(asset: CanonicalAssetResponse): CandidateDependencyAssetItem {
  return {
    assetKey: asset.asset_key,
    assetType: asset.asset_type,
  }
}
