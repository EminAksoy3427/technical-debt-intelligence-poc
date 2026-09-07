export type AppShellNavLink = {
  kind: 'link'
  id: 'overview' | 'candidates' | 'technical-debts' | 'sources'
  label: string
  to: string
}

export type AppShellNavItem = AppShellNavLink

export type AppShellContext = {
  sectionLabel: string
  sectionTo?: string
  pageLabel?: string
}

export const appShellPrimaryNavigation: readonly AppShellNavItem[] = [
  { kind: 'link', id: 'overview', label: 'Overview', to: '/overview' },
  { kind: 'link', id: 'candidates', label: 'Candidates', to: '/candidates' },
  { kind: 'link', id: 'technical-debts', label: 'Technical Debts', to: '/technical-debts' },
  { kind: 'link', id: 'sources', label: 'Sources', to: '/sources' },
]

export function isAppShellNavItemActive(path: string, to: string): boolean {
  return path === to || path.startsWith(`${to}/`)
}

export function resolveAppShellContext(path: string): AppShellContext {
  if (path === '/' || path === '/overview') {
    return {
      sectionLabel: 'Overview',
      sectionTo: '/overview',
    }
  }

  if (path === '/candidates' || path.startsWith('/candidates/')) {
    return {
      sectionLabel: 'Candidates',
      sectionTo: '/candidates',
      pageLabel: path.startsWith('/candidates/') ? 'Candidate' : undefined,
    }
  }

  if (path === '/technical-debts' || path.startsWith('/technical-debts/')) {
    return {
      sectionLabel: 'Technical Debts',
      sectionTo: '/technical-debts',
      pageLabel: path.startsWith('/technical-debts/') ? 'TechnicalDebt' : undefined,
    }
  }

  if (path === '/sources' || path.startsWith('/sources/')) {
    return {
      sectionLabel: 'Sources',
      sectionTo: '/sources',
    }
  }

  return { sectionLabel: 'TechDebt IQ' }
}
