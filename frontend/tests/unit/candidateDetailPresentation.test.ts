import { describe, expect, it } from 'vitest'
import { parseCandidateDetailTab, candidateDetailTabs } from '../../app/utils/candidateDetailTabs'
import { resolveCandidatePresentationTitle } from '../../app/utils/resolveCandidatePresentationTitle'
import {
  assetCriticalityChipLabel,
  candidateGovernanceDistinctionNotice,
  formatDisplayTimestamp,
  formatEvidenceFinding,
  formatSeverityLabel,
  formatSourceSystemLabel,
  uniqueSourceSystems,
  formatToolDisplayLabel,
  formatUppercaseEnumLabel,
  formatEvidenceGroundingLabel,
} from '../../app/utils/candidateDetailDisplay'

describe('parseCandidateDetailTab', () => {
  it('accepts known tab query values and defaults unknown values to overview', () => {
    expect(parseCandidateDetailTab('overview')).toBe('overview')
    expect(parseCandidateDetailTab('evidence')).toBe('evidence')
    expect(parseCandidateDetailTab('investigation')).toBe('investigation')
    expect(parseCandidateDetailTab('validation')).toBe('validation')
    expect(parseCandidateDetailTab('history')).toBe('overview')
    expect(parseCandidateDetailTab(undefined)).toBe('overview')
    expect(parseCandidateDetailTab(['investigation', 'overview'])).toBe('investigation')
  })

  it('defines the four required Candidate Detail tabs', () => {
    expect(candidateDetailTabs.map((tab) => tab.id)).toEqual([
      'overview',
      'evidence',
      'investigation',
      'validation',
    ])
    expect(candidateDetailTabs.map((tab) => tab.label)).toEqual([
      'Overview',
      'Evidence & Context',
      'AI Investigation',
      'Human Validation',
    ])
  })
})

describe('resolveCandidatePresentationTitle', () => {
  it('maps known canonical problem types from the hypothesis template', () => {
    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential HARDCODED_ENDPOINT issue affecting repo-asteria-editor',
        signalTypes: ['HARDCODED_ENDPOINT'],
      }),
    ).toEqual({
      title: 'Hard-coded endpoint',
      canonicalProblemType: 'HARDCODED_ENDPOINT',
    })

    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential MISSING_TIMEOUT issue affecting svc-orbit-catalog',
        signalTypes: ['MISSING_TIMEOUT'],
      }).title,
    ).toBe('Missing network timeout')

    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential PROCESS_LOCAL_STATE issue affecting repo-orbit-catalog',
        signalTypes: ['PROCESS_LOCAL_STATE'],
      }).title,
    ).toBe('Process-local mutable state')

    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential SATD_COMMENT_ADDED issue affecting repo-asteria-editor',
        signalTypes: ['SATD_COMMENT_ADDED'],
      }).title,
    ).toBe('Self-admitted technical debt comment')
  })

  it('maps the recurring incident hypothesis without inventing a new type', () => {
    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential recurring operational incident pattern affecting svc-orbit-catalog',
        signalTypes: ['OPERATIONAL_INCIDENT'],
      }),
    ).toEqual({
      title: 'Recurring incident pattern',
      canonicalProblemType: 'RECURRING_INCIDENT_PATTERN',
    })
  })

  it('falls back to the backend hypothesis when no safe mapping exists', () => {
    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential missing request timeout',
        signalTypes: ['MISSING_TIMEOUT', 'SATD_COMMENT'],
      }),
    ).toEqual({
      title: 'Potential missing request timeout',
      canonicalProblemType: null,
    })

    expect(
      resolveCandidatePresentationTitle({
        hypothesis: 'Potential UNKNOWN_FAMILY issue affecting repo-x',
        signalTypes: ['UNKNOWN_FAMILY'],
      }).title,
    ).toBe('Potential UNKNOWN_FAMILY issue affecting repo-x')
  })
})

describe('candidate detail display formatting', () => {
  it('formats UTC timestamps for display without changing the stored value', () => {
    expect(formatDisplayTimestamp('2026-08-29T12:30:00Z')).toBe('29 Aug 2026, 12:30 UTC')
    expect(formatDisplayTimestamp('2026-08-31T10:00:00+00:00')).toBe('31 Aug 2026, 10:00 UTC')
    expect(formatDisplayTimestamp('not-a-date')).toBe('not-a-date')
  })

  it('formats known source systems without inventing new sources', () => {
    expect(formatSourceSystemLabel('semgrep')).toBe('Semgrep')
    expect(formatSourceSystemLabel('incident-management')).toBe('Incident management')
    expect(formatSeverityLabel('MEDIUM')).toBe('Medium')
    expect(formatSeverityLabel('custom')).toBe('custom')
  })

  it('presents known evidence source references without dropping the raw value', () => {
    expect(
      formatEvidenceFinding(
        'repo-borealis-renderer/renderer_client.py:5:10-5:52 [tdi.python.missing-timeout] A urllib request is made without an explicit timeout.',
      ),
    ).toEqual({
      location: 'renderer_client.py · line 5',
      summary: 'A urllib request is made without an explicit timeout.',
      parsed: true,
    })

    expect(
      formatEvidenceFinding(
        'repo-asteria-editor@abcdef1234567 catalog_client.py:12 TODO: replace the hardcoded URL',
      ),
    ).toEqual({
      location: 'catalog_client.py · line 12',
      summary: 'TODO: replace the hardcoded URL',
      parsed: true,
    })

    expect(formatEvidenceFinding('evidence:member-earlier')).toEqual({
      location: null,
      summary: 'evidence:member-earlier',
      parsed: false,
    })
  })

  it('keeps Candidate versus TechnicalDebt wording explicit for non-validated states', () => {
    expect(candidateGovernanceDistinctionNotice('PENDING')).toBe(
      'Candidate awaiting human validation. Not TechnicalDebt.',
    )
    expect(candidateGovernanceDistinctionNotice('INFORMATION_REQUESTED')).toBe(
      'Candidate awaiting requested information. Not TechnicalDebt.',
    )
    expect(candidateGovernanceDistinctionNotice('REJECTED')).toBe(
      'This Candidate was rejected and is not TechnicalDebt.',
    )
    expect(candidateGovernanceDistinctionNotice('VALIDATED')).toBeNull()
    expect(assetCriticalityChipLabel('MEDIUM')).toBe('Medium criticality')
    expect(assetCriticalityChipLabel('CRITICAL')).toBe('Critical')
  })

  it('collects unique source systems in first-seen order', () => {
    expect(
      uniqueSourceSystems(
        [{ sourceSystem: 'semgrep' }, { sourceSystem: 'git' }],
        [{ sourceSystem: 'semgrep' }, { sourceSystem: 'incident-management' }],
      ),
    ).toEqual(['semgrep', 'git', 'incident-management'])
  })

  it('humanizes known tool names and unknown snake_case tool names safely', () => {
    expect(formatToolDisplayLabel('read_candidate_evidence')).toBe('Read candidate evidence')
    expect(formatToolDisplayLabel('read_candidate_dependency_context')).toBe(
      'Read dependency context',
    )
    expect(formatToolDisplayLabel('read_candidate_enterprise_context')).toBe(
      'Read enterprise context',
    )
    expect(formatToolDisplayLabel('inspect_runtime_graph')).toBe('Inspect runtime graph')
    expect(formatToolDisplayLabel('ReadEvidence')).toBe('ReadEvidence')
    expect(formatUppercaseEnumLabel('READ')).toBe('Read')
    expect(formatUppercaseEnumLabel('ELEVATED')).toBe('Elevated')
    expect(formatUppercaseEnumLabel('Low')).toBe('Low')
    expect(
      formatEvidenceGroundingLabel({
        sourceSystem: 'semgrep',
        sourceReference:
          'repo-borealis-renderer/renderer_client.py:5:10-5:52 [tdi.python.missing-timeout] A urllib request is made without an explicit timeout.',
      }),
    ).toBe('Semgrep · renderer_client.py · line 5')
  })
})
