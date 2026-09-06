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
  'Audit / Assurance',
  'Audit',
  'Assurance',
]

const unimplementedWorkspaceHrefs = [
  '/technical-debt',
  '/technical_debt',
  '/connectors',
  '/sources-and-connectors',
  '/audit',
  '/assurance',
]

describe('AppNavigation implemented workspace', () => {
  it('is rendered from the application layout', () => {
    expect(layout).toContain('NavigationAppNavigation')
  })

  it('exposes Candidates, Technical Debts, and Sources & Connectors as implemented destinations', () => {
    expect(navigation).toContain("label: 'Candidates'")
    expect(navigation).toContain("to: '/candidates'")
    expect(navigation).toContain("label: 'Technical Debts'")
    expect(navigation).toContain("to: '/technical-debts'")
    expect(navigation).toContain("label: 'Sources & Connectors'")
    expect(navigation).toContain("to: '/sources'")
    expect(navigation).toContain('primaryNavigationItems')
    expect(navigation).toContain('NuxtLink :to="item.to"')
  })

  it('does not render unimplemented workspaces or a standalone Connectors workspace', () => {
    for (const label of unimplementedWorkspaceLabels) {
      expect(itemsDeclaration).not.toContain(label)
    }

    expect(itemsDeclaration).not.toContain("label: 'Connectors'")
    expect(itemsDeclaration).not.toContain("label: 'Sources and Connectors'")

    for (const href of unimplementedWorkspaceHrefs) {
      expect(navigation).not.toContain(`'${href}'`)
      expect(navigation).not.toContain(`"${href}"`)
    }

    expect(navigation).not.toMatch(/coming soon/i)
    expect(navigation).not.toMatch(/unavailable/i)
    expect(itemsDeclaration).not.toMatch(/\bplanned\b/i)
  })
})
