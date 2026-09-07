import { candidateProblemTypeLabels } from '../types/candidate'

const HYPOTHESIS_ISSUE_PATTERN = /^Potential ([A-Z][A-Z0-9_]*) issue affecting /

export interface CandidatePresentationTitle {
  title: string
  canonicalProblemType: string | null
}

export function resolveCandidatePresentationTitle(input: {
  hypothesis: string
  signalTypes: readonly string[]
}): CandidatePresentationTitle {
  const fromHypothesis = parseProblemTypeFromHypothesis(input.hypothesis)
  if (fromHypothesis != null) {
    return {
      title: candidateProblemTypeLabels[fromHypothesis] ?? input.hypothesis,
      canonicalProblemType: fromHypothesis,
    }
  }

  const uniqueTypes = [...new Set(input.signalTypes)]
  if (uniqueTypes.length === 1) {
    const signalType = uniqueTypes[0]
    const mappedLabel = signalType == null ? undefined : candidateProblemTypeLabels[signalType]
    if (signalType != null && mappedLabel != null) {
      return {
        title: mappedLabel,
        canonicalProblemType: signalType,
      }
    }
  }

  return {
    title: input.hypothesis,
    canonicalProblemType: null,
  }
}

export function candidateProblemTypeDisplayLabel(problemType: string): string {
  return candidateProblemTypeLabels[problemType] ?? problemType
}

function parseProblemTypeFromHypothesis(hypothesis: string): string | null {
  if (hypothesis.startsWith('Potential recurring operational incident pattern affecting ')) {
    return 'RECURRING_INCIDENT_PATTERN'
  }

  const match = HYPOTHESIS_ISSUE_PATTERN.exec(hypothesis)
  const problemType = match?.[1]
  if (problemType != null && candidateProblemTypeLabels[problemType] != null) {
    return problemType
  }

  return null
}
