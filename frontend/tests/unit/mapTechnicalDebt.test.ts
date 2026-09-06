import { describe, expect, it } from 'vitest'
import type { TechnicalDebtDetail, TechnicalDebtSummary } from '../../app/types/technicalDebtApi'
import {
  toTechnicalDebtDetailPresentation,
  toTechnicalDebtListItem,
} from '../../app/utils/mapTechnicalDebt'

const TECHNICAL_DEBT_ID = '50000000-0000-0000-0000-000000000001'
const CANDIDATE_ID = '20000000-0000-0000-0000-000000000001'

const summary: TechnicalDebtSummary = {
  technical_debt_id: TECHNICAL_DEBT_ID,
  lifecycle_status: 'REGISTERED',
  created_at: '2026-09-06T19:01:00+00:00',
  source_candidate_id: CANDIDATE_ID,
  hypothesis: 'Potential missing request timeout',
  canonical_asset: {
    asset_key: 'svc-orbit-catalog',
    asset_type: 'SERVICE',
  },
}

const detail: TechnicalDebtDetail = {
  technical_debt_id: TECHNICAL_DEBT_ID,
  lifecycle_status: 'REGISTERED',
  created_at: '2026-09-06T19:01:00+00:00',
  source_candidate: {
    candidate_id: CANDIDATE_ID,
    hypothesis: 'Potential missing request timeout',
    correlation_rationale: 'Exact canonical asset and deterministic problem family.',
    canonical_asset: {
      asset_key: 'svc-orbit-catalog',
      asset_type: 'SERVICE',
    },
  },
  creation_human_decision: {
    human_decision_id: '40000000-0000-0000-0000-000000000001',
    decision: 'VALIDATE',
    sequence_number: 1,
    rationale: 'The Candidate is a validated structural issue.',
    actor_reference: 'poc:local-reviewer',
    created_at: '2026-09-06T19:01:00+00:00',
  },
}

describe('toTechnicalDebtListItem', () => {
  it('maps portfolio fields from the list API', () => {
    expect(toTechnicalDebtListItem(summary)).toEqual({
      technicalDebtId: TECHNICAL_DEBT_ID,
      lifecycleStatus: 'REGISTERED',
      createdAt: '2026-09-06T19:01:00+00:00',
      sourceCandidateId: CANDIDATE_ID,
      hypothesis: 'Potential missing request timeout',
      canonicalAssetKey: 'svc-orbit-catalog',
      canonicalAssetType: 'SERVICE',
    })
  })

  it('does not invent risk, effort, owner, or priority', () => {
    const item = toTechnicalDebtListItem(summary)

    expect(item).not.toHaveProperty('risk')
    expect(item).not.toHaveProperty('effort')
    expect(item).not.toHaveProperty('owner')
    expect(item).not.toHaveProperty('priority')
    expect(item).not.toHaveProperty('validatedOwner')
    expect(item).not.toHaveProperty('targetDate')
  })
})

describe('toTechnicalDebtDetailPresentation', () => {
  it('maps TechnicalDebt facts, source Candidate, and creation VALIDATE decision', () => {
    const presentation = toTechnicalDebtDetailPresentation(detail)

    expect(presentation.technicalDebtId).toBe(TECHNICAL_DEBT_ID)
    expect(presentation.lifecycleStatus).toBe('REGISTERED')
    expect(presentation.createdAt).toBe('2026-09-06T19:01:00+00:00')
    expect(presentation.sourceCandidate).toEqual({
      candidateId: CANDIDATE_ID,
      hypothesis: 'Potential missing request timeout',
      correlationRationale: 'Exact canonical asset and deterministic problem family.',
      canonicalAssetKey: 'svc-orbit-catalog',
      canonicalAssetType: 'SERVICE',
    })
    expect(presentation.creationHumanDecision).toEqual({
      humanDecisionId: '40000000-0000-0000-0000-000000000001',
      decision: 'VALIDATE',
      sequenceNumber: 1,
      rationale: 'The Candidate is a validated structural issue.',
      actorReference: 'poc:local-reviewer',
      createdAt: '2026-09-06T19:01:00+00:00',
    })
  })

  it('does not copy Candidate Evidence into TechnicalDebt-owned evidence', () => {
    const presentation = toTechnicalDebtDetailPresentation(detail)

    expect(presentation).not.toHaveProperty('evidence')
    expect(presentation).not.toHaveProperty('signals')
    expect(presentation).not.toHaveProperty('risk')
    expect(presentation).not.toHaveProperty('effort')
    expect(presentation).not.toHaveProperty('owner')
  })
})
