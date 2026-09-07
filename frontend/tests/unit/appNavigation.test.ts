import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const layout = readFrontendSource('layouts/default.vue')
const sidebar = readFrontendSource('components/navigation/AppSidebar.vue')
const topbar = readFrontendSource('components/navigation/AppTopbar.vue')
const navigation = readFrontendSource('utils/appShellNavigation.ts')
const styles = readFrontendSource('assets/css/main.css')
const candidateHeader = readFrontendSource('components/candidate/CandidateDetailHeader.vue')
const technicalDebtHeader = readFrontendSource(
  'components/technicalDebt/TechnicalDebtDetailHeader.vue',
)

const unimplementedWorkspaceHrefs = [
  '/ai-research',
  '/research',
  '/technical-debt',
  '/technical_debt',
  '/connectors',
  '/sources-and-connectors',
  '/audit',
  '/assurance',
]

describe('application navigation shell', () => {
  it('renders the sidebar and topbar from the application layout', () => {
    expect(layout).toContain('NavigationAppSidebar')
    expect(layout).toContain('NavigationAppTopbar')
    expect(layout).toContain('id="main-content"')
    expect(layout).toContain('class="application-content"')
    expect(layout).toContain('Skip to main content')
  })

  it('links only to implemented Overview, Candidates, Technical Debts, and Sources routes', () => {
    expect(navigation).toContain("label: 'Overview'")
    expect(navigation).toContain("to: '/overview'")
    expect(navigation).toContain("label: 'Candidates'")
    expect(navigation).toContain("to: '/candidates'")
    expect(navigation).toContain("label: 'Technical Debts'")
    expect(navigation).toContain("to: '/technical-debts'")
    expect(navigation).toContain("label: 'Sources'")
    expect(navigation).toContain("to: '/sources'")
    expect(sidebar).toContain('appShellPrimaryNavigation')
    expect(sidebar).toContain('NuxtLink')
    expect(sidebar).toContain("aria-current=\"isLinkActive(item.to) ? 'page' : undefined\"")
    expect(sidebar).not.toContain('appShellSecondaryNavigation')
  })

  it('does not keep Later markers or a dead AI Research destination', () => {
    expect(navigation).not.toContain("label: 'AI Research'")
    expect(navigation).not.toContain("id: 'ai-research'")
    expect(navigation).not.toContain("kind: 'placeholder'")
    expect(navigation).not.toContain("statusLabel: 'Later'")
    expect(sidebar).not.toContain('Later')
    expect(sidebar).not.toContain('LATER')
    expect(sidebar).not.toContain('AI Research')
    expect(sidebar).not.toContain('app-sidebar-link--unavailable')
    expect(topbar).not.toContain('Later')
    expect(topbar).not.toContain('AI Research')

    for (const href of unimplementedWorkspaceHrefs) {
      expect(navigation).not.toContain(`'${href}'`)
      expect(navigation).not.toContain(`"${href}"`)
      expect(sidebar).not.toContain(`'${href}'`)
      expect(sidebar).not.toContain(`"${href}"`)
    }
  })

  it('keeps hierarchical breadcrumbs on detail pages instead of duplicating them in the shell', () => {
    expect(topbar).toContain('resolveAppShellContext')
    expect(topbar).toContain('app-topbar-context')
    expect(topbar).toContain('shellContext.sectionLabel')
    expect(topbar).not.toContain('aria-label="Breadcrumb"')
    expect(topbar).not.toContain('app-topbar-breadcrumb')
    expect(candidateHeader).toContain('aria-label="Breadcrumb"')
    expect(candidateHeader).toContain('to="/candidates"')
    expect(candidateHeader).toContain('aria-current="page">Candidate')
    expect(technicalDebtHeader).toContain('aria-label="Breadcrumb"')
    expect(technicalDebtHeader).toContain('to="/technical-debts"')
    expect(technicalDebtHeader).toContain('aria-current="page">TechnicalDebt')
  })

  it('does not invent global search or a user account control', () => {
    expect(topbar).toContain('app-topbar-environment')
    expect(topbar).toContain('PoC')
    expect(topbar).not.toMatch(/type="search"/)
    expect(topbar).not.toMatch(/placeholder="Search/)
    expect(topbar).not.toMatch(/\bSign in\b/)
    expect(topbar).not.toMatch(/\bAccount\b/)
    expect(topbar).not.toMatch(/\bAvatar\b/)
    expect(sidebar).not.toMatch(/type="search"/)
    expect(sidebar).toContain('TechDebt IQ')
    expect(sidebar).toContain('Intelligence &amp; Governance')
    expect(sidebar).toContain('Proof of concept')
  })

  it('defines the shell design tokens without replacing page content styles', () => {
    expect(styles).toContain('--color-background')
    expect(styles).toContain('--color-surface')
    expect(styles).toContain('--color-surface-subtle')
    expect(styles).toContain('--color-sidebar')
    expect(styles).toContain('--color-sidebar-hover')
    expect(styles).toContain('--color-sidebar-active')
    expect(styles).toContain('--color-ink')
    expect(styles).toContain('--color-muted')
    expect(styles).toContain('--color-border')
    expect(styles).toContain('--color-primary')
    expect(styles).toContain('--color-primary-hover')
    expect(styles).toContain('--color-success')
    expect(styles).toContain('--color-warning')
    expect(styles).toContain('--color-danger')
    expect(styles).toContain('--color-info')
    expect(styles).toContain(':focus-visible')
    expect(styles).toContain('max-width: 76rem')
    expect(styles).toContain('.candidate-pool')
    expect(styles).toContain('.candidate-detail')
    expect(styles).toContain('.human-validation-form')
    expect(styles).toContain('.sources-page')
  })
})
