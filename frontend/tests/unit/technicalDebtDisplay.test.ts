import { describe, expect, it } from 'vitest'
import {
  actionProposalTargetRepository,
  displayRecordedValue,
  hasRecordedValue,
  humanDecisionTypeDisplayLabel,
  newestActionProposal,
  previousActionProposals,
  technicalDebtInventoryCountLabel,
  technicalDebtLifecycleStatusDisplayLabel,
  technicalDebtPresentationTitle,
} from '../../app/utils/technicalDebtDisplay'

describe('technicalDebtPresentationTitle', () => {
  it('uses the source Candidate hypothesis when it is present', () => {
    expect(technicalDebtPresentationTitle('Potential missing request timeout')).toBe(
      'Potential missing request timeout',
    )
  })

  it('falls back without inventing a polished debt title', () => {
    expect(technicalDebtPresentationTitle('')).toBe('TechnicalDebt record')
    expect(technicalDebtPresentationTitle('   ')).toBe('TechnicalDebt record')
  })
})

describe('displayRecordedValue', () => {
  it('returns a safe fallback for missing or blank values', () => {
    expect(displayRecordedValue(null)).toBe('Not recorded')
    expect(displayRecordedValue(undefined)).toBe('Not recorded')
    expect(displayRecordedValue('')).toBe('Not recorded')
    expect(displayRecordedValue('  ')).toBe('Not recorded')
    expect(displayRecordedValue('svc-orbit-catalog')).toBe('svc-orbit-catalog')
    expect(hasRecordedValue('rationale')).toBe(true)
    expect(hasRecordedValue('')).toBe(false)
  })
})

describe('technicalDebtLifecycleStatusDisplayLabel', () => {
  it('labels the persisted REGISTERED status and keeps unknown values readable', () => {
    expect(technicalDebtLifecycleStatusDisplayLabel('REGISTERED')).toBe('Registered')
    expect(technicalDebtLifecycleStatusDisplayLabel('UNEXPECTED')).toBe('UNEXPECTED')
  })
})

describe('humanDecisionTypeDisplayLabel', () => {
  it('labels VALIDATE and keeps unknown decisions readable', () => {
    expect(humanDecisionTypeDisplayLabel('VALIDATE')).toBe('Validate')
    expect(humanDecisionTypeDisplayLabel('UNKNOWN_DECISION')).toBe('UNKNOWN_DECISION')
  })
})

describe('technicalDebtInventoryCountLabel', () => {
  it('uses TechnicalDebt record wording', () => {
    expect(technicalDebtInventoryCountLabel(1)).toBe('1 TechnicalDebt record')
    expect(technicalDebtInventoryCountLabel(3)).toBe('3 TechnicalDebt records')
  })
})

describe('action proposal display helpers', () => {
  it('formats the target repository from backend owner and name', () => {
    expect(actionProposalTargetRepository('tdi-demo-target', 'tdi-action-preview')).toBe(
      'tdi-demo-target/tdi-action-preview',
    )
  })

  it('treats the last backend-ordered proposal as the current preview', () => {
    const proposals = [{ id: 'earlier' }, { id: 'later' }]

    expect(newestActionProposal(proposals)).toEqual({ id: 'later' })
    expect(previousActionProposals(proposals)).toEqual([{ id: 'earlier' }])
    expect(newestActionProposal([])).toBeNull()
    expect(previousActionProposals([{ id: 'only' }])).toEqual([])
  })
})
