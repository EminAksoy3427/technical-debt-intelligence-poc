import {
  candidateAssetTypeDisplayLabel,
  type CandidateListItem,
} from '../types/candidate'
import type { AssetType } from '../types/candidateApi'

const ASSET_TYPE_ORDER: readonly AssetType[] = ['APPLICATION', 'SERVICE', 'REPOSITORY']

export interface CandidateCollectionAssetType {
  assetType: string
  label: string
}

export interface CandidateCollectionSummary {
  candidateCount: number
  signalsRepresented: number
  evidenceRepresented: number
  assetTypesRepresented: CandidateCollectionAssetType[]
}

/**
 * Collection-level facts from GET /api/v1/candidates list items only.
 * signal_count and evidence_count are summed across returned Candidates;
 * they are not system-wide signal or evidence totals.
 */
export function summarizeCandidateCollection(
  candidates: readonly CandidateListItem[],
): CandidateCollectionSummary {
  const assetTypes = new Set<string>()
  let signalsRepresented = 0
  let evidenceRepresented = 0

  for (const candidate of candidates) {
    signalsRepresented += candidate.signalCount
    evidenceRepresented += candidate.evidenceCount
    assetTypes.add(candidate.assetType)
  }

  const knownTypes = ASSET_TYPE_ORDER.filter((type) => assetTypes.has(type))
  const remainingTypes = [...assetTypes]
    .filter((type) => !ASSET_TYPE_ORDER.includes(type as AssetType))
    .sort()

  return {
    candidateCount: candidates.length,
    signalsRepresented,
    evidenceRepresented,
    assetTypesRepresented: [...knownTypes, ...remainingTypes].map((assetType) => ({
      assetType,
      label: candidateAssetTypeDisplayLabel(assetType),
    })),
  }
}
