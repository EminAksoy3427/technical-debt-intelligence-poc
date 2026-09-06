import { describe, expect, it } from 'vitest'
import {
  buildHumanValidationRequest,
  humanValidationClientValidationMessage,
} from '../../app/utils/buildHumanValidationRequest'

describe('humanValidationClientValidationMessage', () => {
  it('requires a nonblank rationale for VALIDATE and REJECT', () => {
    expect(humanValidationClientValidationMessage('VALIDATE', '   ', '')).toBe(
      'Rationale is required.',
    )
    expect(humanValidationClientValidationMessage('REJECT', '', '')).toBe('Rationale is required.')
    expect(
      humanValidationClientValidationMessage(
        'VALIDATE',
        'The Candidate is a validated structural issue.',
        '',
      ),
    ).toBeNull()
  })

  it('requires nonblank requested information for REQUEST_INFO', () => {
    expect(humanValidationClientValidationMessage('REQUEST_INFO', '', '   ')).toBe(
      'Requested information is required.',
    )
    expect(
      humanValidationClientValidationMessage('REQUEST_INFO', '', 'Who owns the catalog service?'),
    ).toBeNull()
  })
})

describe('buildHumanValidationRequest', () => {
  it('includes only contract fields for VALIDATE', () => {
    const payload = buildHumanValidationRequest({
      decision: 'VALIDATE',
      expectedGovernanceRevision: 0,
      rationale: '  Structural issue confirmed.  ',
      requestedInformation: 'ignored',
    })

    expect(Object.keys(payload).sort()).toEqual([
      'decision',
      'expected_governance_revision',
      'rationale',
    ])
    expect(payload).toEqual({
      decision: 'VALIDATE',
      rationale: 'Structural issue confirmed.',
      expected_governance_revision: 0,
    })
  })

  it('cannot include actor, approval, role, or TechnicalDebt identifiers', () => {
    const payload = buildHumanValidationRequest({
      decision: 'REJECT',
      expectedGovernanceRevision: 1,
      rationale: 'Not a structural issue.',
      requestedInformation: '',
    })
    const keys = Object.keys(payload)

    expect(keys).not.toContain('actor_reference')
    expect(keys).not.toContain('role')
    expect(keys).not.toContain('approval')
    expect(keys).not.toContain('authorization')
    expect(keys).not.toContain('provider')
    expect(keys).not.toContain('model')
    expect(keys).not.toContain('tool')
    expect(keys).not.toContain('technical_debt_id')
    expect(keys).not.toContain('state')
  })
})
