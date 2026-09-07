export interface SourceIngestionPipelineStage {
  id: string
  name: string
  description: string
}

export const sourceIngestionPipelineHeading = 'How source data enters the system'

export const sourceIngestionPipelineNote =
  'This is the operating model for canonical ingestion. It is not live telemetry. Semgrep, Git, and Incident currently normalize source-specific records without passing through the Connector Registry.'

export const sourceIngestionPipelineStages: readonly SourceIngestionPipelineStage[] = [
  {
    id: 'external-source',
    name: 'External system / controlled source',
    description:
      'Source-specific observations such as Semgrep findings, Git SATD comments, incident records, or lifecycle exports.',
  },
  {
    id: 'adapter',
    name: 'Connector / source adapter / loader',
    description:
      'Registered connectors acquire SourceObservation. Other implemented sources load through source adapters rather than the Connector Registry.',
  },
  {
    id: 'observation',
    name: 'SourceObservation',
    description:
      'An acquired source-specific record with SourceObservationRef provenance and observed_at time. This is not a Signal.',
  },
  {
    id: 'normalizer',
    name: 'Normalizer',
    description:
      'Maps a supported observation into canonical technical-debt signal semantics.',
  },
  {
    id: 'normalized-signal',
    name: 'NormalizedSignal + Evidence',
    description:
      'The canonical ingestion output: a Signal with matching, nonempty Evidence and preserved provenance.',
  },
  {
    id: 'correlation',
    name: 'Correlation',
    description: 'Groups related NormalizedSignals into a reviewable Candidate.',
  },
  {
    id: 'candidate',
    name: 'Candidate',
    description:
      'A suspected technical-debt case. A Candidate is not TechnicalDebt.',
  },
]
