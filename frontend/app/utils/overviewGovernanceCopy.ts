export const overviewGovernanceHeading = 'Governance boundary'

export const overviewGovernanceLead = 'AI investigates. Humans govern.'

export const overviewGovernanceAiTitle = 'AI Investigation'

export const overviewGovernanceAiCopy =
  'Reads approved context and produces grounded findings and recommendations. AI is decision support, not governance authority.'

export const overviewGovernanceHumanTitle = 'Human Validation'

export const overviewGovernanceHumanCopy =
  'Records the authoritative governance decision. Agent Investigation grants no lifecycle authority.'

export const overviewGovernanceDecisions = [
  {
    id: 'VALIDATE',
    name: 'VALIDATE',
    consequence:
      'The Candidate becomes governed TechnicalDebt according to the existing lifecycle. REGISTERED is the current TechnicalDebt status and is not approval of remediation work.',
  },
  {
    id: 'REJECT',
    name: 'REJECT',
    consequence:
      'The Candidate is not validated. The Candidate is not deleted and does not become TechnicalDebt.',
  },
  {
    id: 'REQUEST_INFO',
    name: 'REQUEST_INFO',
    consequence:
      'More information is required before a final VALIDATE or REJECT decision. The Candidate is not TechnicalDebt.',
  },
] as const
