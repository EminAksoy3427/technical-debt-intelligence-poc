export interface OverviewOperatingModelStage {
  id: string
  name: string
  description: string
}

export const overviewOperatingModelHeading = 'How the system works'

export const overviewOperatingModelNote =
  'This is the PoC operating model. It is explanatory, not live pipeline telemetry.'

export const overviewOperatingModelStages: readonly OverviewOperatingModelStage[] = [
  {
    id: 'sources',
    name: 'Sources',
    description: 'Engineering and operational observations enter through source adapters.',
  },
  {
    id: 'signals-evidence',
    name: 'Signals & Evidence',
    description:
      'Observations are normalized into source-independent signals with provenance.',
  },
  {
    id: 'correlation',
    name: 'Correlation',
    description: 'Related observations are assembled into a reviewable Candidate.',
  },
  {
    id: 'candidate',
    name: 'Candidate',
    description:
      'A suspected technical-debt case. A Candidate is not governed TechnicalDebt before Human Validation.',
  },
  {
    id: 'ai-investigation',
    name: 'AI Investigation',
    description:
      'Governed AI analyzes available evidence and context and proposes findings. AI is decision support, not governance authority.',
  },
  {
    id: 'human-validation',
    name: 'Human Validation',
    description: 'A human reviewer records VALIDATE, REJECT, or REQUEST_INFO.',
  },
  {
    id: 'technical-debt',
    name: 'TechnicalDebt',
    description:
      'Created only after a human VALIDATE decision in the existing governance lifecycle.',
  },
]
