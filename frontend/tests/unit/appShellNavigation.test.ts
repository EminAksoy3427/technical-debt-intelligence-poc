import { describe, expect, it } from 'vitest'
import {
  appShellPrimaryNavigation,
  isAppShellNavItemActive,
  resolveAppShellContext,
} from '../../app/utils/appShellNavigation'

describe('app shell navigation', () => {
  it('links the implemented Overview, Candidates, Technical Debts, and Sources destinations', () => {
    expect(appShellPrimaryNavigation.map((item) => item.id)).toEqual([
      'overview',
      'candidates',
      'technical-debts',
      'sources',
    ])
    expect(appShellPrimaryNavigation.map((item) => item.label)).toEqual([
      'Overview',
      'Candidates',
      'Technical Debts',
      'Sources',
    ])
    expect(appShellPrimaryNavigation.every((item) => item.kind === 'link')).toBe(true)
    expect(appShellPrimaryNavigation.map((item) => item.to)).toEqual([
      '/overview',
      '/candidates',
      '/technical-debts',
      '/sources',
    ])
  })

  it('marks nested candidate and technical-debt routes as active without crossing workspaces', () => {
    expect(isAppShellNavItemActive('/candidates', '/candidates')).toBe(true)
    expect(isAppShellNavItemActive('/candidates/abc', '/candidates')).toBe(true)
    expect(isAppShellNavItemActive('/technical-debts', '/candidates')).toBe(false)
    expect(isAppShellNavItemActive('/sources', '/sources')).toBe(true)
    expect(isAppShellNavItemActive('/overview', '/overview')).toBe(true)
    expect(isAppShellNavItemActive('/candidates', '/overview')).toBe(false)
    expect(isAppShellNavItemActive('/technical-debts/abc', '/technical-debts')).toBe(true)
  })

  it('resolves section context for list and detail routes', () => {
    expect(resolveAppShellContext('/')).toEqual({
      sectionLabel: 'Overview',
      sectionTo: '/overview',
    })
    expect(resolveAppShellContext('/overview')).toEqual({
      sectionLabel: 'Overview',
      sectionTo: '/overview',
    })
    expect(resolveAppShellContext('/candidates')).toEqual({
      sectionLabel: 'Candidates',
      sectionTo: '/candidates',
      pageLabel: undefined,
    })
    expect(resolveAppShellContext('/candidates/abc')).toEqual({
      sectionLabel: 'Candidates',
      sectionTo: '/candidates',
      pageLabel: 'Candidate',
    })
    expect(resolveAppShellContext('/technical-debts/abc')).toEqual({
      sectionLabel: 'Technical Debts',
      sectionTo: '/technical-debts',
      pageLabel: 'TechnicalDebt',
    })
    expect(resolveAppShellContext('/sources')).toEqual({
      sectionLabel: 'Sources',
      sectionTo: '/sources',
    })
  })
})
