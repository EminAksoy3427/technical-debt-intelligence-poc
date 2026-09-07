import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const testsDirectory = dirname(fileURLToPath(import.meta.url))
const frontendAppDirectory = join(testsDirectory, '../../app')

function readFrontendSource(relativePath: string): string {
  return readFileSync(join(frontendAppDirectory, relativePath), 'utf8')
}

describe('Sources page source', () => {
  const page = readFrontendSource('pages/sources/index.vue')
  const inventory = readFrontendSource('components/connector/ConnectorInventory.vue')
  const signalIngestion = readFrontendSource(
    'components/sources/SourcesSignalIngestion.vue',
  )
  const pipeline = readFrontendSource(
    'components/sources/SourcesIngestionPipeline.vue',
  )
  const architecture = readFrontendSource(
    'components/sources/SourcesArchitectureNotes.vue',
  )
  const copy = readFrontendSource('utils/sourcesPageCopy.ts')
  const capabilities = readFrontendSource('utils/sourceIngestionCapabilities.ts')
  const pipelineCopy = readFrontendSource('utils/sourceIngestionPipeline.ts')
  const apiClient = readFrontendSource('composables/useConnectorApi.ts')
  const styles = readFrontendSource('assets/css/main.css')
  const sources = [
    page,
    inventory,
    signalIngestion,
    pipeline,
    architecture,
    copy,
    capabilities,
    pipelineCopy,
  ].join('\n')

  it('loads inventory through useConnectorApi.getConnectors and GET /api/v1/connectors', () => {
    expect(page).toContain('useConnectorApi()')
    expect(page).toContain('getConnectors')
    expect(page).toContain('toConnectorSummary')
    expect(page).toContain('annotateRegisteredConnector')
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

  it('renders Sources copy and the four inventory states without failing the page', () => {
    expect(copy).toContain("export const sourcesPageTitle = 'Sources'")
    expect(copy).toContain('Registered connectors could not be loaded.')
    expect(copy).toContain('Loading registered connectors.')
    expect(copy).toContain('No connectors are currently registered.')
    expect(page).toContain("viewState === 'loading'")
    expect(page).toContain("viewState === 'error'")
    expect(page).toContain("viewState === 'empty'")
    expect(page).toContain("viewState === 'ready'")
    expect(page).toContain('role="status"')
    expect(page).toContain('role="alert"')
    expect(page).toContain('ConnectorInventory')
    expect(page.indexOf('SourcesSignalIngestion')).toBeGreaterThan(
      page.indexOf("viewState === 'error'"),
    )
    expect(page).toContain('SourcesIngestionPipeline')
    expect(page).toContain('SourcesArchitectureNotes')
  })

  it('does not present health, connectivity, marketplace, or GitHub internals', () => {
    expect(sources).not.toMatch(/\bHealthy\b/)
    expect(sources).not.toMatch(/\bConnected\b/)
    expect(sources).not.toMatch(/\bOnline\b/)
    expect(sources).not.toMatch(/\bLive\b/)
    expect(sources).not.toMatch(/\bSynced\b/)
    expect(sources).not.toContain('Last run')
    expect(sources).not.toContain('Last sync')
    expect(sources).not.toContain('uptime')
    expect(sources).not.toContain('99.9%')
    expect(sources).not.toContain('events/min')
    expect(sources).not.toContain('Last error')
    expect(sources).not.toContain('Checkpoint')
    expect(sources).not.toContain('Run Connector')
    expect(sources).not.toContain('Install')
    expect(sources).not.toContain('Enable')
    expect(sources).not.toContain('Disable')
    expect(sources).not.toContain('GITHUB_TOKEN')
    expect(sources).not.toContain('github_repository_owner')
    expect(sources).not.toContain('github_repository_name')
    expect(sources).not.toContain('EminAksoy3427')
    expect(sources).not.toContain('technical-debt-connector-demo')
    expect(sources).not.toContain('Kafka')
    expect(sources).not.toContain('Jira')
    expect(sources).not.toContain('SonarQube')
    expect(sources).not.toContain('Bitbucket')
  })

  it('presents registered connectors as compact rows with disclosed technical fields', () => {
    expect(inventory).toContain('connector.displayName')
    expect(inventory).toContain('connector.roleLabel')
    expect(inventory).toContain('connectorStatusLabel(connector.status)')
    expect(inventory).toContain('badge badge--neutral')
    expect(inventory).not.toContain('badge--info')
    expect(inventory).not.toContain('badge--success')
    expect(inventory).toContain('connector.capabilitySummary')
    expect(inventory).toContain('Technical details')
    expect(inventory).toContain('<details')
    expect(inventory).toContain('connectorTechnicalDetailRows')
    expect(inventory).not.toContain('<table')
    expect(inventory).not.toContain('to=')
    expect(inventory).not.toContain('NuxtLink')
  })

  it('distinguishes connector registration from Signal ingestion', () => {
    expect(copy).toContain(
      'Registration describes configured capability. It does not imply runtime health or successful ingestion.',
    )
    expect(copy).toContain(
      'Not every ingestion source is a registered connector, and not every registered connector produces Signals.',
    )
    expect(copy).toContain('Connector registration is not runtime connectivity.')
    expect(copy).toContain('Acquisition is not Signal production.')
    expect(capabilities).toContain('GitHub Issues is not listed')
    expect(signalIngestion).toContain('sourceIngestionCapabilities')
    expect(signalIngestion).not.toContain('github-issues')
  })

  it('explains provenance, normalization, and in-code extensibility', () => {
    expect(copy).toContain('SourceObservationRef')
    expect(copy).toContain('source_system and source_record_id')
    expect(copy).toContain('NormalizedSignal contract')
    expect(copy).toContain('in-code extension path')
    expect(copy).not.toContain('Any system can be connected instantly')
    expect(architecture).toContain('sourcesProvenanceNote')
    expect(architecture).toContain('sourcesExtensibilityNote')
    expect(architecture).toContain('sourcesNormalizationNote')
  })

  it('does not introduce Candidate Detail or other N+1 requests', () => {
    expect(page).not.toMatch(/\bgetCandidate\b/)
    expect(page).not.toContain('getCandidates')
    expect(page).not.toContain('listTechnicalDebts')
    expect(page).not.toContain('getTechnicalDebt')
    expect(page).not.toContain('getAgentRun')
  })

  it('keeps the pipeline vertical on a narrow layout without a wide table', () => {
    expect(pipeline).toContain('<ol')
    expect(pipeline).not.toContain('<table')
    expect(styles).toContain('.sources-pipeline')
    expect(styles).toContain('overflow-x: clip')
    expect(styles).toContain('grid-template-columns: minmax(0, 1fr)')
    expect(styles).not.toContain('.sources-pipeline-table')
    expect(inventory).not.toContain('min-width: 40rem')
  })
})
