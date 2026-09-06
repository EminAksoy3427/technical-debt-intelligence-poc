import { describe, expect, it } from 'vitest'
import { availableHumanValidationActions } from '../../app/utils/availableHumanValidationActions'

describe('availableHumanValidationActions', () => {
  it('exposes VALIDATE, REJECT, and REQUEST_INFO for PENDING', () => {
    expect(availableHumanValidationActions('PENDING')).toEqual([
      'VALIDATE',
      'REJECT',
      'REQUEST_INFO',
    ])
  })

  it('keeps VALIDATE, REJECT, and REQUEST_INFO available after INFORMATION_REQUESTED', () => {
    expect(availableHumanValidationActions('INFORMATION_REQUESTED')).toEqual([
      'VALIDATE',
      'REJECT',
      'REQUEST_INFO',
    ])
  })

  it('hides Human Validation actions after VALIDATED', () => {
    expect(availableHumanValidationActions('VALIDATED')).toEqual([])
  })

  it('hides Human Validation actions after REJECTED', () => {
    expect(availableHumanValidationActions('REJECTED')).toEqual([])
  })
})
