import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

describe('Sources & Connectors page source', () => {
  const page = readFrontendSource('pages/sources/index.vue')
  const table = readFrontendSource('components/connector/ConnectorInventoryTable.vue')
  const apiClient = readFrontendSource('composables/useConnectorApi.ts')

  it('loads inventory through useConnectorApi.getConnectors and GET /api/v1/connectors', () => {
    expect(page).toContain('useConnectorApi()')
    expect(page).toContain('getConnectors')
    expect(page).toContain('toConnectorSummary')
    expect(page).toContain('server: false')
    expect(apiClient).toContain("const CONNECTORS_PATH = '/api/v1/connectors'")
    expect(apiClient).toContain('$fetch')
    expect(page).not.toContain('$fetch(')
    expect(page).not.toContain('axios')
    expect(page).not.toContain('getMock')
    expect(apiClient).not.toContain('api.github.com')
  })

  it('does not hard-code a connector inventory or mock fallback', () => {
    expect(page).not.toMatch(/connector_id:\s*'dependency-lifecycle'/)
    expect(page).not.toMatch(/connectorId:\s*'dependency-lifecycle'/)
    expect(page).not.toMatch(/connector_id:\s*'github-issues'/)
    expect(page).not.toContain('[{')
    expect(page).not.toContain('mockConnectors')
    expect(page).not.toContain('fallbackConnectors')
  })

  it('renders Sources & Connectors copy and the four inventory states', () => {
    expect(page).toContain('Sources & Connectors')
    expect(page).toContain('Loading sources and connectors.')
    expect(page).toContain('Sources and connectors could not be loaded.')
    expect(page).toContain('No connectors are currently registered.')
    expect(page).toContain("viewState === 'loading'")
    expect(page).toContain("viewState === 'error'")
    expect(page).toContain("viewState === 'empty'")
    expect(page).toContain("viewState === 'ready'")
    expect(page).toContain('role="status"')
    expect(page).toContain('role="alert"')
    expect(page).toContain('ConnectorInventoryTable')
  })

  it('does not present health, execution, marketplace, or GitHub internals', () => {
    const combined = `${page}\n${table}`
    expect(combined).not.toMatch(/\bHealthy\b/)
    expect(combined).not.toMatch(/\bConnected\b/)
    expect(combined).not.toMatch(/\bOnline\b/)
    expect(combined).not.toMatch(/\bLive\b/)
    expect(combined).not.toContain('Last run')
    expect(combined).not.toContain('Last error')
    expect(combined).not.toContain('Checkpoint')
    expect(combined).not.toContain('Run Connector')
    expect(combined).not.toContain('Install')
    expect(combined).not.toContain('Enable')
    expect(combined).not.toContain('Disable')
    expect(combined).not.toContain('GITHUB_TOKEN')
    expect(combined).not.toContain('github_repository_owner')
    expect(combined).not.toContain('github_repository_name')
    expect(combined).not.toContain('EminAksoy3427')
    expect(combined).not.toContain('technical-debt-connector-demo')
  })

  it('displays connector inventory columns from mapped presentation fields', () => {
    expect(table).toContain('Connector')
    expect(table).toContain('Source system')
    expect(table).toContain('Transport')
    expect(table).toContain('Access')
    expect(table).toContain('Registration')
    expect(table).toContain('connector.displayName')
    expect(table).toContain('connector.connectorId')
    expect(table).toContain('connector.sourceSystem')
    expect(table).toContain('connectorTransportLabel(connector.transport)')
    expect(table).toContain('connectorAccessLabel(connector.readOnly)')
    expect(table).toContain('connectorStatusLabel(connector.status)')
    expect(table).not.toContain('to=')
    expect(table).not.toContain('NuxtLink')
  })
})
