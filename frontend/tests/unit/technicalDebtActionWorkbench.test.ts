import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'
import { buildTechnicalDebtAuditTimeline } from '../../app/utils/technicalDebtAudit'
import type {
  ActionApprovalPresentation,
  ActionExecutionPresentation,
  ActionPolicyDecisionPresentation,
  ActionProposalPresentation,
  ActionVerificationPresentation,
} from '../../app/types/technicalDebt'

const frontendAppDirectory = join(import.meta.dirname, '..', '..', 'app')
const workbench = readFileSync(
  join(frontendAppDirectory, 'components/technicalDebt/TechnicalDebtActionWorkbench.vue'),
  'utf8',
)
const detailPage = readFileSync(
  join(frontendAppDirectory, 'pages/technical-debts/[id].vue'),
  'utf8',
)

describe('TechnicalDebt action workbench', () => {
  it('keeps prepare, approve, execute, and verify as separate actions', () => {
    expect(detailPage).toContain('<TechnicalDebtActionPreparation')
    expect(detailPage).toContain('<TechnicalDebtActionWorkbench')
    expect(workbench).toContain('Approve External Action')
    expect(workbench).toContain('Execute Approved Action')
    expect(workbench).toContain('Verify External Action')
    expect(workbench).not.toContain('performAction')
  })

  it('uses persisted IDs to retain an older approved proposal relationship', () => {
    expect(workbench).toContain(
      'proposal.actionProposalId === recordedApproval.value?.actionProposalId',
    )
    expect(workbench).toContain('approval.actionProposalId === currentPreview.value?.actionProposalId')
    expect(workbench).toContain('belongs to an earlier proposal')
    expect(workbench).not.toContain('active proposal')
    expect(workbench).not.toContain('superseded')
  })

  it('presents UNKNOWN, FAIL, and UNAVAILABLE without collapsing their meanings', () => {
    expect(workbench).toContain("selectedExecution.status === 'UNKNOWN'")
    expect(workbench).toContain('External outcome is uncertain')
    expect(workbench).not.toContain('Retry execution')
    expect(workbench).not.toContain('Retry GitHub creation')
    expect(workbench).toContain("selectedVerification.result === 'FAIL'")
    expect(workbench).toContain('Read-back completed, but the approved semantics differ.')
    expect(workbench).toContain('Verification could not currently complete.')
    expect(workbench).not.toContain('TechnicalDebt is CLOSED')
    expect(workbench).not.toContain('TechnicalDebt is RESOLVED')
  })

  it('uses only the exact persisted external URL as a safe link', () => {
    expect(workbench).toContain(':href="selectedExecution.externalIssueUrl"')
    expect(workbench).toContain('target="_blank"')
    expect(workbench).toContain('rel="noopener noreferrer"')
    expect(workbench).not.toContain('github.com/${')
  })

  it('makes the real-write boundary and backend authority explicit', () => {
    expect(workbench).toContain('may create a real GitHub Issue')
    expect(workbench).toContain('backend policy evaluation')
    expect(workbench).toContain('Approval is not policy authorization')
    expect(workbench).toContain('does not change TechnicalDebt lifecycle')
    expect(workbench).not.toMatch(/\b(owner|risk|effort|priority) assignment\b/i)
  })
})

describe('TechnicalDebt persisted audit timeline', () => {
  it('orders persisted records deterministically and keeps ID relationships', () => {
    const proposal: ActionProposalPresentation = {
      actionProposalId: 'proposal-1',
      technicalDebtId: 'debt-1',
      actionType: 'CREATE_GITHUB_ISSUE',
      targetRepositoryOwner: 'persisted-owner',
      targetRepositoryName: 'persisted-repository',
      title: 'Persisted title',
      body: 'Persisted body',
      payloadFingerprint: 'a'.repeat(64),
      reconciliationMarker: 'persisted-marker',
      preparedBy: 'persisted-actor',
      createdAt: '2026-09-07T10:01:00Z',
    }
    const approval: ActionApprovalPresentation = {
      actionApprovalId: 'approval-1',
      actionProposalId: proposal.actionProposalId,
      payloadFingerprint: proposal.payloadFingerprint,
      actorReference: 'persisted-approver',
      createdAt: '2026-09-07T10:02:00Z',
    }
    const policy: ActionPolicyDecisionPresentation = {
      actionPolicyDecisionId: 'policy-1',
      actionProposalId: proposal.actionProposalId,
      actionApprovalId: approval.actionApprovalId,
      decision: 'ALLOW',
      ruleId: 'persisted-rule',
      reasonCode: 'POLICY_ALLOWED',
      createdAt: '2026-09-07T10:03:00Z',
    }
    const execution: ActionExecutionPresentation = {
      actionExecutionId: 'execution-1',
      actionProposalId: proposal.actionProposalId,
      technicalDebtId: 'debt-1',
      actionType: 'CREATE_GITHUB_ISSUE',
      creationPolicyDecisionId: policy.actionPolicyDecisionId,
      status: 'SUCCEEDED',
      externalIssueId: 10,
      externalIssueNumber: 10,
      externalIssueUrl: 'https://example.test/persisted/10',
      safeErrorCategory: null,
      startedAt: '2026-09-07T10:04:00Z',
      completedAt: '2026-09-07T10:05:00Z',
    }
    const verification: ActionVerificationPresentation = {
      actionVerificationId: 'verification-1',
      actionExecutionId: execution.actionExecutionId,
      result: 'PASS',
      observedIssueNumber: 10,
      observedIssueUrl: execution.externalIssueUrl,
      safeReasonCode: null,
      createdAt: '2026-09-07T10:06:00Z',
    }

    const timeline = buildTechnicalDebtAuditTimeline({
      technicalDebtId: 'debt-1',
      technicalDebtCreatedAt: '2026-09-07T10:00:00Z',
      actionProposals: [proposal],
      actionApprovals: [approval],
      actionPolicyDecisions: [policy],
      actionExecutions: [execution],
      actionVerifications: [verification],
    })

    expect(timeline.map((item) => item.label)).toEqual([
      'Technical Debt Registered',
      'Action Proposal Prepared',
      'Human Approval Recorded',
      'Policy Allowed',
      'External Execution Succeeded',
      'Verification Passed',
    ])
    expect(timeline[2]?.relationship).toBe('Proposal proposal-1')
    expect(timeline[5]?.relationship).toBe('Execution execution-1')
  })

  it('projects DENY, UNKNOWN, FAIL, and UNAVAILABLE as distinct persisted facts', () => {
    const emptyBase = {
      technicalDebtId: 'debt-1',
      technicalDebtCreatedAt: '2026-09-07T10:00:00Z',
      actionProposals: [],
      actionApprovals: [],
    }
    const timeline = buildTechnicalDebtAuditTimeline({
      ...emptyBase,
      actionPolicyDecisions: [{
        actionPolicyDecisionId: 'policy-deny', actionProposalId: 'proposal-1',
        actionApprovalId: null, decision: 'DENY', ruleId: 'rule',
        reasonCode: 'APPROVAL_MISSING', createdAt: '2026-09-07T10:01:00Z',
      }],
      actionExecutions: [{
        actionExecutionId: 'execution-unknown', actionProposalId: 'proposal-1',
        technicalDebtId: 'debt-1', actionType: 'CREATE_GITHUB_ISSUE',
        creationPolicyDecisionId: 'policy-deny', status: 'UNKNOWN', externalIssueId: null,
        externalIssueNumber: null, externalIssueUrl: null,
        safeErrorCategory: 'TRANSPORT_UNKNOWN', startedAt: '2026-09-07T10:02:00Z',
        completedAt: '2026-09-07T10:03:00Z',
      }],
      actionVerifications: [
        { actionVerificationId: 'verify-fail', actionExecutionId: 'execution-unknown',
          result: 'FAIL', observedIssueNumber: 1, observedIssueUrl: 'https://example.test/1',
          safeReasonCode: 'TITLE_MISMATCH', createdAt: '2026-09-07T10:04:00Z' },
        { actionVerificationId: 'verify-unavailable', actionExecutionId: 'execution-unknown',
          result: 'UNAVAILABLE', observedIssueNumber: null, observedIssueUrl: null,
          safeReasonCode: 'TRANSPORT_UNAVAILABLE', createdAt: '2026-09-07T10:05:00Z' },
      ],
    })

    expect(timeline.map((item) => item.label)).toContain('Policy Denied')
    expect(timeline.map((item) => item.label)).toContain('External Execution Unknown')
    expect(timeline.map((item) => item.label)).toContain('Verification Failed')
    expect(timeline.map((item) => item.label)).toContain('Verification Unavailable')
    expect(JSON.stringify(timeline)).not.toMatch(/CLOSED|RESOLVED/)
  })
})
