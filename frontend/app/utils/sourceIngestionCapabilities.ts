import { implementedSignalSources } from './implementedSignalSources'

/**
 * Sources-page presentation for verified Signal-producing ingestion.
 * IDs must remain a subset of implementedSignalSources.
 *
 * Semgrep: backend/app/semgrep_ingestion.py via infrastructure/semgrep.py
 * Git SATD: backend/app/git_history_ingestion.py via infrastructure/git_history.py
 * Incident: backend/app/incident_ingestion.py from persisted Incident records
 * Dependency lifecycle: backend/app/dependency_lifecycle_ingestion.py
 *   and optional connector normalize_dependency_lifecycle_observation
 *
 * GitHub Issues is not listed: it is acquisition-only and does not produce Signals.
 */
export interface SourceIngestionCapability {
  id: string
  name: string
  observationKind: string
  normalizedRole: string
  explanation: string
}

const capabilityDetails: Record<
  string,
  Omit<SourceIngestionCapability, 'id' | 'name'> & { displayName?: string }
> = {
  semgrep: {
    observationKind: 'Static analysis',
    normalizedRole: 'NormalizedSignal + Evidence',
    explanation: 'Produces normalized findings from controlled Semgrep rules.',
  },
  git: {
    displayName: 'Git SATD',
    observationKind: 'Repository history',
    normalizedRole: 'NormalizedSignal + Evidence',
    explanation: 'Detects added self-admitted technical-debt comments.',
  },
  'incident-management': {
    observationKind: 'Operational observations',
    normalizedRole: 'NormalizedSignal + Evidence',
    explanation: 'Normalizes incident records into operational signals.',
  },
  'dependency-lifecycle': {
    observationKind: 'Lifecycle observations',
    normalizedRole: 'NormalizedSignal + Evidence',
    explanation: 'Normalizes dependency end-of-life findings.',
  },
}

export const sourceIngestionCapabilities: readonly SourceIngestionCapability[] =
  implementedSignalSources.map((source) => {
    const details = capabilityDetails[source.id]
    return {
      id: source.id,
      name: details?.displayName ?? source.name,
      observationKind: details?.observationKind ?? 'Source observation',
      normalizedRole: details?.normalizedRole ?? 'NormalizedSignal + Evidence',
      explanation: details?.explanation ?? source.description,
    }
  })

export const sourceIngestionCapabilitiesHeading = 'Signal ingestion capabilities'

export const sourceIngestionCapabilitiesNote =
  'These implemented loaders and normalizers produce NormalizedSignal and Evidence. They are not the Connector Registry, and they are not live connection or health status.'
