export const technicalDebtsPageTitle = 'Technical Debts'

export const technicalDebtsPageIntroduction =
  'Governed technical-debt records created through Human Validation.'

export const technicalDebtsPageDistinction =
  'Candidates appear here only after a persisted VALIDATE decision.'

export const technicalDebtsInventoryLoading = 'Loading Technical Debts.'

export const technicalDebtsInventoryError = 'Technical Debts could not be loaded.'

export const technicalDebtsInventoryEmptyTitle =
  'No TechnicalDebt records have been created yet.'

export const technicalDebtsInventoryEmptyExplanation =
  'TechnicalDebt records are created when a human reviewer validates a Candidate.'

export const technicalDebtsReviewCandidatesLabel = 'Review Candidates'

export const technicalDebtsDetailLoading = 'Loading TechnicalDebt details.'

export const technicalDebtsDetailNotFoundTitle = 'TechnicalDebt was not found.'

export const technicalDebtsDetailNotFoundExplanation =
  'The requested TechnicalDebt does not exist.'

export const technicalDebtsDetailInvalidTitle = 'The TechnicalDebt identifier is invalid.'

export const technicalDebtsDetailInvalidExplanation =
  'The requested TechnicalDebt identifier is not a valid TechnicalDebt ID.'

export const technicalDebtsDetailErrorTitle = 'TechnicalDebt details could not be loaded.'

export const technicalDebtsDetailErrorExplanation =
  'TechnicalDebt details could not be loaded. Try again later.'

export const technicalDebtsSourceCandidateIntroduction =
  'Evidence remains on the source Candidate. This page does not copy Candidate Evidence into TechnicalDebt-owned evidence.'

export const technicalDebtsCreationDecisionIntroduction =
  'The VALIDATE decision that created this TechnicalDebt. Audit actor is server-owned attribution, not verified employee identity.'

export const technicalDebtsActionPreparationTitle = 'Action Preparation'

export const technicalDebtsActionPreparationIntroduction =
  'This is a prepared external action preview. No external change has been performed.'

export const technicalDebtsActionPreparationPrepareHint =
  'Prepare GitHub Issue creates a persisted preview only. It does not create a GitHub issue.'

export const technicalDebtsActionPreparationPrepareLabel = 'Prepare GitHub Issue'

export const technicalDebtsActionPreparationCurrentPreviewTitle =
  'Current prepared preview'

export const technicalDebtsActionPreparationEmptyPreview =
  'No GitHub issue preview has been prepared yet.'

export const technicalDebtsActionPreparationPreviousHeading = (count: number): string =>
  `Previous prepared proposals (${count})`
