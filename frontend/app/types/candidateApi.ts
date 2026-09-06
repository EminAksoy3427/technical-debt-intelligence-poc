/**
 * FastAPI Candidate API wire DTOs.
 * These types describe JSON from GET /api/v1/candidates and
 * GET /api/v1/candidates/{candidate_id}. They are not the FP-01A
 * presentation model and are not TechnicalDebt.
 */

import type { CandidateGovernance } from './humanValidationApi'

export type AssetType = 'APPLICATION' | 'SERVICE' | 'REPOSITORY'

export type AssetCriticality = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export type AssetLifecycleStatus = 'PLANNED' | 'ACTIVE' | 'RETIRED'

export type OwnershipRole = 'PRIMARY' | 'SUPPORTING'

export type AssetRelationshipType = 'CONTAINS' | 'IMPLEMENTED_BY' | 'DEPENDS_ON'

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'

export interface CanonicalAssetResponse {
  asset_key: string
  asset_type: AssetType
}

export interface EnterpriseAssetResponse extends CanonicalAssetResponse {
  name: string
  criticality: AssetCriticality
  lifecycle_status: AssetLifecycleStatus
}

export interface CandidateResponse {
  candidate_id: string
  signal_ids: string[]
  evidence_ids: string[]
  canonical_asset: CanonicalAssetResponse
  hypothesis: string
  correlation_rationale: string
}

export interface SignalResponse {
  signal_id: string
  source_system: string
  source_record_id: string
  detected_at: string
  signal_type: string
  affected_asset: CanonicalAssetResponse
  severity: string | null
  evidence_ids: string[]
}

export interface EvidenceResponse {
  evidence_id: string
  source_system: string
  source_reference: string
  captured_at: string
  reference_uri: string | null
}

export interface AssetOwnershipResponse {
  asset_key: string
  team_key: string
  ownership_role: OwnershipRole
}

export interface TeamResponse {
  team_key: string
  name: string
}

export interface EnterpriseAssetOwnershipResponse {
  asset_ownership: AssetOwnershipResponse
  team: TeamResponse
}

export interface AssetRelationshipResponse {
  source_asset_key: string
  target_asset_key: string
  relationship_type: AssetRelationshipType
}

export interface IncidentResponse {
  incident_key: string
  primary_affected_asset_key: string
  severity: IncidentSeverity
  title: string
  started_at: string
  resolved_at: string | null
}

export interface CandidateEnterpriseContextResponse {
  candidate_id: string
  enterprise_asset: EnterpriseAssetResponse
  enterprise_ownerships: EnterpriseAssetOwnershipResponse[]
  direct_relationships: AssetRelationshipResponse[]
  direct_incidents: IncidentResponse[]
}

export interface CandidateDependencyContextResponse {
  candidate_id: string
  candidate_asset: CanonicalAssetResponse
  dependency_anchors: CanonicalAssetResponse[]
  direct_dependencies: CanonicalAssetResponse[]
  direct_dependents: CanonicalAssetResponse[]
  reachable_dependents: CanonicalAssetResponse[]
}

export interface CandidateSummaryResponse {
  candidate_id: string
  hypothesis: string
  canonical_asset: CanonicalAssetResponse
  enterprise_asset: EnterpriseAssetResponse
  signal_count: number
  evidence_count: number
}

export interface CandidateListResponse {
  items: CandidateSummaryResponse[]
  count: number
}

export interface CandidateDetailResponse {
  candidate: CandidateResponse
  signals: SignalResponse[]
  evidence: EvidenceResponse[]
  enterprise_context: CandidateEnterpriseContextResponse
  dependency_context: CandidateDependencyContextResponse
  governance: CandidateGovernance
}
