import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

const navigation = readFrontendSource('components/navigation/AppNavigation.vue')
const layout = readFrontendSource('layouts/default.vue')
const itemsDeclaration = navigation.slice(
  navigation.indexOf('const primaryNavigationItems'),
  navigation.indexOf('</script>'),
)

const unimplementedWorkspaceLabels = [
  'Technical Debt',
  'Sources & Connectors',
  'Sources and Connectors',
  'Audit / Assurance',
  'Audit',
  'Assurance',
  'Connectors',
]

const unimplementedWorkspaceHrefs = [
  '/technical-debt',
  '/technical_debt',
  '/sources',
  '/connectors',
  '/sources-and-connectors',
  '/audit',
  '/assurance',
]

describe('AppNavigation implemented workspace', () => {
  it('is rendered from the application layout', () => {
    expect(layout).toContain('NavigationAppNavigation')
  })

  it('exposes Candidates as the only implemented primary destination', () => {
    expect(navigation).toContain("label: 'Candidates'")
    expect(navigation).toContain("to: '/candidates'")
    expect(navigation).toContain('primaryNavigationItems')
    expect(navigation).toContain('NuxtLink :to="item.to"')
  })

  it('does not render unimplemented workspaces or dead links', () => {
    for (const label of unimplementedWorkspaceLabels) {
      expect(itemsDeclaration).not.toContain(label)
    }

    for (const href of unimplementedWorkspaceHrefs) {
      expect(navigation).not.toContain(`'${href}'`)
      expect(navigation).not.toContain(`"${href}"`)
    }

    expect(navigation).not.toMatch(/coming soon/i)
    expect(navigation).not.toMatch(/unavailable/i)
    expect(itemsDeclaration).not.toMatch(/\bplanned\b/i)
  })
})
