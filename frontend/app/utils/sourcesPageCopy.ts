export const sourcesPageTitle = 'Sources'

export const sourcesPageIntroduction =
  'Inspect the source and connector capabilities that feed technical-debt intelligence.'

export const sourcesRegistrationHelper =
  'Registration describes configured capability. It does not imply runtime health or successful ingestion.'

export const sourcesArchitectureDistinctionHeading = 'Connector registration and ingestion are different'

export const sourcesArchitectureDistinctionNote =
  'The Connector Registry is an explicit acquisition composition inventory. Signal ingestion is a separate canonical boundary that produces NormalizedSignal and Evidence. Not every ingestion source is a registered connector, and not every registered connector produces Signals.'

export const sourcesRegisteredConnectorsHeading = 'Registered connectors'

export const sourcesRegisteredConnectorsNote =
  'Application composition inventory. Listing connectors does not execute them.'

export const sourcesRegisteredConnectorsLoading = 'Loading registered connectors.'

export const sourcesRegisteredConnectorsError = 'Registered connectors could not be loaded.'

export const sourcesRegisteredConnectorsEmpty = 'No connectors are currently registered.'

export const sourcesNormalizationHeading = 'Why normalization exists'

export const sourcesNormalizationNote =
  'Different sources speak different languages: Semgrep findings, operational incidents, Git SATD comments, and dependency end-of-life records. Normalization converts them into a common NormalizedSignal contract so correlation and governance do not depend on each external tool.'

export const sourcesProvenanceHeading = 'Provenance is preserved'

export const sourcesProvenanceNote =
  'Normalized Signal and Evidence retain SourceObservationRef identity — source_system and source_record_id — so evidence can be traced back to its origin. This page does not fabricate source links or expose raw source payloads.'

export const sourcesExtensibilityHeading = 'Adding another source'

export const sourcesExtensibilityNote =
  'Additional sources can integrate by implementing the source boundary and mapping external observations into the canonical NormalizedSignal contract. That is an in-code extension path, not runtime plugin discovery or a connector marketplace.'

export const sourcesSemanticsHeading = 'Connector semantics'

export const sourcesSemanticsNotes = [
  'Connector registration is not runtime connectivity.',
  'Connector registration is not connector health.',
  'Connector registration is not successful ingestion.',
  'Acquisition is not Signal production.',
  'A Candidate is not TechnicalDebt.',
] as const
