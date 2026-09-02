import type { CandidateListItem } from '../types/candidate'
import type { CandidateSummaryResponse } from '../types/candidateApi'

export function toCandidateListItem(summary: CandidateSummaryResponse): CandidateListItem {
  return {
    id: summary.candidate_id,
    title: summary.hypothesis,
    assetName: summary.enterprise_asset.name,
    assetType: summary.enterprise_asset.asset_type,
    signalCount: summary.signal_count,
    evidenceCount: summary.evidence_count,
  }
}
