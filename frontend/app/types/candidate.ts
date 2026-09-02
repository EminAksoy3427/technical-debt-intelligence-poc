import type { AssetType } from './candidateApi'

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
 * Factual D1 presentation model for Candidate Detail.
 * Enterprise ownership, relationships, incidents, and dependency context
 * are deferred to FP-01B-D2.
 */
export interface CandidateDetailPresentation {
  candidate: CandidateDetailCore
  signals: CandidateSignalItem[]
  evidence: CandidateEvidenceItem[]
}
