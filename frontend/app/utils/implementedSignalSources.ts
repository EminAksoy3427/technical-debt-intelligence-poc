/**
 * Implemented ingestion capabilities proven by current backend normalizers.
 * This is not connector health, live sync status, or the connector registry.
 *
 * Semgrep: backend/app/semgrep_ingestion.py
 * Git SATD: backend/app/git_history_ingestion.py
 * Incident management: backend/app/incident_ingestion.py
 * Dependency lifecycle: backend/app/dependency_lifecycle_ingestion.py
 *
 * Acquisition-only GitHub Issues is registered in the connector inventory
 * and does not produce Signals, so it is not listed here.
 */
export interface ImplementedSignalSource {
  id: string
  name: string
  description: string
}

export const implementedSignalSources: readonly ImplementedSignalSource[] = [
  {
    id: 'semgrep',
    name: 'Semgrep',
    description: 'Static-analysis findings',
  },
  {
    id: 'git',
    name: 'Git',
    description: 'SATD observations',
  },
  {
    id: 'incident-management',
    name: 'Incident management',
    description: 'Operational incident observations',
  },
  {
    id: 'dependency-lifecycle',
    name: 'Dependency lifecycle',
    description: 'Lifecycle and end-of-life observations',
  },
]

export const implementedSignalSourcesHeading = 'Signal sources'

export const implementedSignalSourcesCapabilityLabel = 'Implemented ingestion capability'

export const implementedSignalSourcesNote =
  'These are implemented ingestion capabilities. They are not live connection or health status.'
