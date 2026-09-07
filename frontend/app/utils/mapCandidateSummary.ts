import type { CandidateListItem } from '../types/candidate'
import type { CandidateSummaryResponse } from '../types/candidateApi'
import { resolveCandidatePresentationTitle } from './resolveCandidatePresentationTitle'

export function toCandidateListItem(summary: CandidateSummaryResponse): CandidateListItem {
  const hypothesis = summary.hypothesis.trim() || 'Candidate'
  const presentation = resolveCandidatePresentationTitle({
    hypothesis,
    signalTypes: [],
  })
  const assetName = summary.enterprise_asset.name.trim()
  const assetKey =
    summary.enterprise_asset.asset_key.trim() || summary.canonical_asset.asset_key.trim()

  return {
    id: summary.candidate_id,
    title: hypothesis,
    presentationTitle: presentation.title.trim() || hypothesis,
    assetName: assetName || assetKey || 'Unknown asset',
    assetType: summary.enterprise_asset.asset_type,
    signalCount: summary.signal_count,
    evidenceCount: summary.evidence_count,
  }
}
