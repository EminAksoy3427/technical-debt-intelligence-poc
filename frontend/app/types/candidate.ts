import type {
  AssetCriticality,
  AssetLifecycleStatus,
  AssetRelationshipType,
  AssetType,
  IncidentSeverity,
  OwnershipRole,
} from './candidateApi'

/**
 * Frontend presentation model for the Candidate Pool.
 * Mapped from CandidateSummaryResponse for pool display and client-side filtering.
 * This is not the canonical backend Candidate contract and is not TechnicalDebt.
 */
export interface CandidateListItem {
  id: string
  title: string
  assetName: string
  assetType: AssetType
  signalCount: number
  evidenceCount: number
}

export const candidatePoolAssetTypeLabels: Record<AssetType, string> = {
  APPLICATION: 'Application',
  SERVICE: 'Service',
  REPOSITORY: 'Repository',
}

/**
 * Factual Candidate identity for the Detail view.
 * Mapped from CandidateDetailResponse. This is not TechnicalDebt and does not
 * represent validation, risk, effort, priority, or ownership decisions.
 */
export interface CandidateDetailCore {
  candidateId: string
  hypothesis: string
  canonicalAssetKey: string
  canonicalAssetType: AssetType
  assetDisplayName: string
  correlationRationale: string
}

/**
 * Factual Signal membership for the Candidate Detail view.
 * A Signal is not a Candidate and does not prove Candidate validity.
 */
export interface CandidateSignalItem {
  signalId: string
  signalType: string
  sourceSystem: string
  sourceRecordId: string
  affectedAssetKey: string
  affectedAssetType: AssetType
  detectedAt: string
  severity: string | null
}

/**
 * Factual Evidence provenance for the Candidate Detail view.
 * Evidence is not validation.
 */
export interface CandidateEvidenceItem {
  evidenceId: string
  sourceSystem: string
  sourceReference: string
  capturedAt: string
  referenceUri: string | null
}

/**
 * Factual enterprise asset context for Candidate Detail.
 * Criticality is asset criticality, not Candidate or TechnicalDebt risk.
 * Lifecycle status is asset lifecycle status.
 */
export interface CandidateEnterpriseAssetContext {
  name: string
  assetKey: string
  assetType: AssetType
  criticality: AssetCriticality
  lifecycleStatus: AssetLifecycleStatus
}

/**
 * Factual enterprise asset ownership for Candidate Detail.
 * These records describe ownership of the enterprise asset, not Candidate
 * ownership and not validated TechnicalDebt ownership.
 */
export interface CandidateEnterpriseOwnershipItem {
  teamName: string
  teamKey: string
  ownershipRole: OwnershipRole
}

/**
 * Factual recorded enterprise relationship. This is not causality.
 */
export interface CandidateDirectRelationshipItem {
  sourceAssetKey: string
  targetAssetKey: string
  relationshipType: AssetRelationshipType
}

/**
 * Factual associated incident context. An incident does not prove Candidate causality.
 * Incident severity is not Candidate risk.
 */
export interface CandidateDirectIncidentItem {
  incidentKey: string
  title: string
  severity: IncidentSeverity
  startedAt: string
  resolvedAt: string | null
  primaryAffectedAssetKey: string
}

export interface CandidateEnterpriseContextPresentation {
  asset: CandidateEnterpriseAssetContext
  ownerships: CandidateEnterpriseOwnershipItem[]
  relationships: CandidateDirectRelationshipItem[]
  incidents: CandidateDirectIncidentItem[]
}

/**
 * Factual dependency graph asset reference returned by the backend.
 */
export interface CandidateDependencyAssetItem {
  assetKey: string
  assetType: AssetType
}

/**
 * Factual dependency reachability context returned by the backend.
 * Reachable dependents are graph connectivity facts, not guaranteed impact.
 */
export interface CandidateDependencyContextPresentation {
  candidateAsset: CandidateDependencyAssetItem
  dependencyAnchors: CandidateDependencyAssetItem[]
  directDependencies: CandidateDependencyAssetItem[]
  directDependents: CandidateDependencyAssetItem[]
  reachableDependents: CandidateDependencyAssetItem[]
}

/**
 * Factual Candidate Detail presentation model.
 * This is not TechnicalDebt and does not represent validation, risk, effort,
 * priority, ownership decisions, causality, or guaranteed impact.
 */
export interface CandidateDetailPresentation {
  candidate: CandidateDetailCore
  signals: CandidateSignalItem[]
  evidence: CandidateEvidenceItem[]
  enterpriseContext: CandidateEnterpriseContextPresentation
  dependencyContext: CandidateDependencyContextPresentation
}
