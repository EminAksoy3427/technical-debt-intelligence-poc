export const candidateDetailTabIds = [
  'overview',
  'evidence',
  'investigation',
  'validation',
] as const

export type CandidateDetailTabId = (typeof candidateDetailTabIds)[number]

export interface CandidateDetailTabDefinition {
  id: CandidateDetailTabId
  label: string
  panelId: string
  tabId: string
}

export const candidateDetailTabs: readonly CandidateDetailTabDefinition[] = [
  {
    id: 'overview',
    label: 'Overview',
    panelId: 'candidate-overview',
    tabId: 'candidate-tab-overview',
  },
  {
    id: 'evidence',
    label: 'Evidence & Context',
    panelId: 'candidate-evidence-context',
    tabId: 'candidate-tab-evidence',
  },
  {
    id: 'investigation',
    label: 'AI Investigation',
    panelId: 'candidate-agent-investigation',
    tabId: 'candidate-tab-investigation',
  },
  {
    id: 'validation',
    label: 'Human Validation',
    panelId: 'candidate-human-validation',
    tabId: 'candidate-tab-validation',
  },
] as const

export function parseCandidateDetailTab(value: unknown): CandidateDetailTabId {
  const raw = Array.isArray(value) ? value[0] : value
  if (
    typeof raw === 'string' &&
    (candidateDetailTabIds as readonly string[]).includes(raw)
  ) {
    return raw as CandidateDetailTabId
  }

  return 'overview'
}
