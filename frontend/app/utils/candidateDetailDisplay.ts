import { candidateAssetCriticalityLabels } from '../types/candidate'
import type { AssetCriticality } from '../types/candidateApi'
import type { CandidateGovernanceState } from '../types/humanValidationApi'

const MONTHS = [
  'Jan',
  'Feb',
  'Mar',
  'Apr',
  'May',
  'Jun',
  'Jul',
  'Aug',
  'Sep',
  'Oct',
  'Nov',
  'Dec',
] as const

const knownSourceSystemLabels: Record<string, string> = {
  semgrep: 'Semgrep',
  git: 'Git',
  'github-issues': 'GitHub Issues',
  'incident-management': 'Incident management',
  'dependency-lifecycle': 'Dependency lifecycle',
}

const knownSeverityLabels: Record<string, string> = {
  LOW: 'Low',
  MEDIUM: 'Medium',
  HIGH: 'High',
  CRITICAL: 'Critical',
}

export function formatDisplayTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }

  const month = MONTHS[date.getUTCMonth()]
  if (month == null) {
    return value
  }

  const day = date.getUTCDate()
  const year = date.getUTCFullYear()
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${day} ${month} ${year}, ${hours}:${minutes} UTC`
}

export function formatSourceSystemLabel(sourceSystem: string): string {
  const known = knownSourceSystemLabels[sourceSystem]
  if (known != null) {
    return known
  }

  return sourceSystem
    .split(/[-_]+/)
    .filter((part) => part.length > 0)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1).toLowerCase())
    .join(' ')
}

export function formatSeverityLabel(severity: string): string {
  return knownSeverityLabels[severity] ?? severity
}

const knownToolDisplayLabels: Record<string, string> = {
  read_candidate_evidence: 'Read candidate evidence',
  read_candidate_dependency_context: 'Read dependency context',
  read_candidate_enterprise_context: 'Read enterprise context',
}

export function formatToolDisplayLabel(toolId: string): string {
  const known = knownToolDisplayLabels[toolId]
  if (known != null) {
    return known
  }

  const parts = toolId.split(/[-_]+/).filter((part) => part.length > 0)
  if (parts.length <= 1) {
    return toolId
  }

  return parts
    .map((part, index) => {
      const lower = part.toLowerCase()
      if (index === 0) {
        return lower.charAt(0).toUpperCase() + lower.slice(1)
      }
      return lower
    })
    .join(' ')
}

export function formatUppercaseEnumLabel(value: string): string {
  if (value.length === 0 || value !== value.toUpperCase()) {
    return value
  }

  const lower = value.toLowerCase()
  return lower.charAt(0).toUpperCase() + lower.slice(1)
}

export function formatEvidenceGroundingLabel(input: {
  sourceSystem: string
  sourceReference: string
}): string {
  const sourceLabel = formatSourceSystemLabel(input.sourceSystem)
  const finding = formatEvidenceFinding(input.sourceReference)
  if (finding.location == null) {
    return sourceLabel
  }

  return `${sourceLabel} · ${finding.location}`
}

export function uniqueSourceSystems(
  signals: readonly { sourceSystem: string }[],
  evidence: readonly { sourceSystem: string }[],
): string[] {
  const seen = new Set<string>()
  const ordered: string[] = []

  for (const item of [...signals, ...evidence]) {
    if (seen.has(item.sourceSystem)) {
      continue
    }
    seen.add(item.sourceSystem)
    ordered.push(item.sourceSystem)
  }

  return ordered
}

export interface EvidenceFindingDisplay {
  location: string | null
  summary: string
  parsed: boolean
}

const SEMGREP_FINDING_PATTERN =
  /^(.*?):(\d+):\d+-\d+:\d+\s+\[[^\]]+\]\s+(.+)$/s
const GIT_FINDING_PATTERN = /^\S+@[0-9a-f]{7,40}\s+(\S+):(\d+)\s+(.+)$/i

export function formatEvidenceFinding(sourceReference: string): EvidenceFindingDisplay {
  const semgrepMatch = SEMGREP_FINDING_PATTERN.exec(sourceReference)
  const semgrepPath = semgrepMatch?.[1]
  const semgrepLine = semgrepMatch?.[2]
  const semgrepMessage = semgrepMatch?.[3]
  if (semgrepPath != null && semgrepLine != null && semgrepMessage != null) {
    return {
      location: `${fileNameFromPath(semgrepPath)} · line ${semgrepLine}`,
      summary: semgrepMessage,
      parsed: true,
    }
  }

  const gitMatch = GIT_FINDING_PATTERN.exec(sourceReference)
  const gitPath = gitMatch?.[1]
  const gitLine = gitMatch?.[2]
  const gitMessage = gitMatch?.[3]
  if (gitPath != null && gitLine != null && gitMessage != null) {
    return {
      location: `${fileNameFromPath(gitPath)} · line ${gitLine}`,
      summary: gitMessage,
      parsed: true,
    }
  }

  return {
    location: null,
    summary: sourceReference,
    parsed: false,
  }
}

export function assetCriticalityChipLabel(criticality: AssetCriticality): string {
  if (criticality === 'CRITICAL') {
    return 'Critical'
  }

  return `${candidateAssetCriticalityLabels[criticality]} criticality`
}

export function candidateGovernanceBadgeClass(state: CandidateGovernanceState): string {
  if (state === 'PENDING') {
    return 'badge badge--info'
  }
  if (state === 'INFORMATION_REQUESTED') {
    return 'badge badge--attention'
  }
  if (state === 'VALIDATED') {
    return 'badge badge--success'
  }
  return 'badge badge--danger'
}

export function candidateGovernanceDistinctionNotice(
  state: CandidateGovernanceState,
): string | null {
  if (state === 'VALIDATED') {
    return null
  }
  if (state === 'REJECTED') {
    return 'This Candidate was rejected and is not TechnicalDebt.'
  }
  if (state === 'INFORMATION_REQUESTED') {
    return 'Candidate awaiting requested information. Not TechnicalDebt.'
  }
  return 'Candidate awaiting human validation. Not TechnicalDebt.'
}

function fileNameFromPath(path: string): string {
  const separator = path.lastIndexOf('/')
  if (separator < 0) {
    return path
  }
  return path.slice(separator + 1)
}
