import { describe, expect, it } from 'vitest'
import {
  formatHumanValidationEvidenceCount,
  HUMAN_VALIDATION_DISTINCTION,
  HUMAN_VALIDATION_REJECT_HELPER,
  HUMAN_VALIDATION_REQUEST_INFO_HELPER,
  HUMAN_VALIDATION_VALIDATE_CONSEQUENCE,
  humanDecisionResultingGovernanceLabel,
  humanDecisionResultingGovernanceState,
  humanValidationDecisionDescriptions,
  humanValidationDecisionLabel,
  humanValidationSubmitLabel,
} from '../../app/utils/humanValidationDecisionCopy'

describe('humanValidationDecisionCopy', () => {
  it('uses human-readable labels instead of raw enum strings', () => {
    expect(humanValidationDecisionLabel('VALIDATE')).toBe('Validate')
    expect(humanValidationDecisionLabel('REJECT')).toBe('Reject')
    expect(humanValidationDecisionLabel('REQUEST_INFO')).toBe('Request information')
    expect(humanValidationSubmitLabel('VALIDATE')).toBe('Validate Candidate')
    expect(humanValidationSubmitLabel('REJECT')).toBe('Reject Candidate')
    expect(humanValidationSubmitLabel('REQUEST_INFO')).toBe('Request information')
  })

  it('describes backend-supported decisions without approval or remediation language', () => {
    expect(humanValidationDecisionDescriptions.VALIDATE).toBe(
      'Confirm this Candidate as TechnicalDebt.',
    )
    expect(humanValidationDecisionDescriptions.REJECT).toBe(
      'Evidence does not support validation.',
    )
    expect(humanValidationDecisionDescriptions.REQUEST_INFO).toBe(
      'More evidence or context is required.',
    )
    expect(HUMAN_VALIDATION_VALIDATE_CONSEQUENCE).toContain('TechnicalDebt')
    expect(HUMAN_VALIDATION_VALIDATE_CONSEQUENCE).toContain('creates the corresponding governed record')
    expect(HUMAN_VALIDATION_REJECT_HELPER).toContain('not deleted')
    expect(HUMAN_VALIDATION_REQUEST_INFO_HELPER).toContain('not validated or rejected')
    expect(HUMAN_VALIDATION_DISTINCTION).toContain('human reviewer')

    const copy = [
      ...Object.values(humanValidationDecisionDescriptions),
      HUMAN_VALIDATION_VALIDATE_CONSEQUENCE,
      HUMAN_VALIDATION_REJECT_HELPER,
      HUMAN_VALIDATION_REQUEST_INFO_HELPER,
      HUMAN_VALIDATION_DISTINCTION,
    ].join('\n')

    expect(copy).not.toMatch(/approv/i)
    expect(copy).not.toMatch(/remediat/i)
    expect(copy).not.toMatch(/\bexecute\b/i)
    expect(copy).not.toMatch(/\bclose\b/i)
  })

  it('maps each decision to the resulting backend governance state', () => {
    expect(humanDecisionResultingGovernanceState('VALIDATE')).toBe('VALIDATED')
    expect(humanDecisionResultingGovernanceState('REJECT')).toBe('REJECTED')
    expect(humanDecisionResultingGovernanceState('REQUEST_INFO')).toBe(
      'INFORMATION_REQUESTED',
    )
    expect(humanDecisionResultingGovernanceLabel('VALIDATE')).toBe('Validated')
    expect(humanDecisionResultingGovernanceLabel('REJECT')).toBe('Rejected')
    expect(humanDecisionResultingGovernanceLabel('REQUEST_INFO')).toBe(
      'Information requested',
    )
  })

  it('formats evidence counts without inventing investigation status', () => {
    expect(formatHumanValidationEvidenceCount(0)).toBe('None recorded')
    expect(formatHumanValidationEvidenceCount(1)).toBe('1 item')
    expect(formatHumanValidationEvidenceCount(3)).toBe('3 items')
  })
})
