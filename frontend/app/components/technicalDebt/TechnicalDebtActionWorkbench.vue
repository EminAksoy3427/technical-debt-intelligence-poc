<script setup lang="ts">
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import {
  toActionApprovalPresentation,
  toActionExecutionPresentation,
  toActionVerificationPresentation,
} from '~/utils/mapTechnicalDebt'
import { submitGovernedMutation } from '~/utils/submitGovernedAction'
import { newestActionProposal } from '~/utils/technicalDebtDisplay'
import type {
  ActionApprovalPresentation,
  ActionExecutionPresentation,
  ActionVerificationPresentation,
  TechnicalDebtDetailPresentation,
} from '~/types/technicalDebt'

const props = defineProps<{
  presentation: TechnicalDebtDetailPresentation
  refreshTechnicalDebt: () => Promise<unknown>
}>()

const { approveActionProposal, executeActionProposal, verifyActionExecution } =
  useTechnicalDebtApi()

const approving = ref(false)
const executing = ref(false)
const verifying = ref(false)
const approvalMessage = ref('')
const executionMessage = ref('')
const verificationMessage = ref('')
const localApprovals = ref<ActionApprovalPresentation[]>([])
const localExecutions = ref<ActionExecutionPresentation[]>([])
const localVerifications = ref<ActionVerificationPresentation[]>([])

const approvals = computed(() => mergeApprovals(props.presentation.actionApprovals))
const executions = computed(() => mergeExecutions(props.presentation.actionExecutions))
const verifications = computed(() => mergeVerifications(props.presentation.actionVerifications))
const currentPreview = computed(() => newestActionProposal(props.presentation.actionProposals))
const currentPreviewApproval = computed(() =>
  currentPreview.value == null
    ? null
    : (approvals.value.find(
        (approval) => approval.actionProposalId === currentPreview.value?.actionProposalId,
      ) ?? null),
)
const recordedApproval = computed(() => approvals.value.at(-1) ?? null)
const approvedProposal = computed(() =>
  recordedApproval.value == null
    ? null
    : (props.presentation.actionProposals.find(
        (proposal) => proposal.actionProposalId === recordedApproval.value?.actionProposalId,
      ) ?? null),
)
const selectedExecution = computed(() => executions.value.at(-1) ?? null)
const selectedVerification = computed(() => {
  if (selectedExecution.value == null) {
    return null
  }
  return (
    verifications.value
      .filter(
        (verification) =>
          verification.actionExecutionId === selectedExecution.value?.actionExecutionId,
      )
      .at(-1) ?? null
  )
})
const executionAlreadyRecorded = computed(() => {
  if (approvedProposal.value == null) {
    return false
  }
  return executions.value.some(
    (execution) => execution.actionProposalId === approvedProposal.value?.actionProposalId,
  )
})
const canVerify = computed(() =>
  ['SUCCEEDED', 'UNKNOWN', 'IN_PROGRESS'].includes(selectedExecution.value?.status ?? ''),
)

function mergeApprovals(server: readonly ActionApprovalPresentation[]) {
  return [
    ...server,
    ...localApprovals.value.filter(
      (local) => !server.some((item) => item.actionApprovalId === local.actionApprovalId),
    ),
  ]
}

function mergeExecutions(server: readonly ActionExecutionPresentation[]) {
  return [
    ...server,
    ...localExecutions.value.filter(
      (local) => !server.some((item) => item.actionExecutionId === local.actionExecutionId),
    ),
  ]
}

function mergeVerifications(server: readonly ActionVerificationPresentation[]) {
  return [
    ...server,
    ...localVerifications.value.filter(
      (local) =>
        !server.some((item) => item.actionVerificationId === local.actionVerificationId),
    ),
  ]
}

async function approve() {
  const proposal = currentPreview.value
  if (approving.value || proposal == null) return
  approving.value = true
  approvalMessage.value = ''
  const result = await submitGovernedMutation({
    mutate: () =>
      approveActionProposal(
        props.presentation.technicalDebtId,
        proposal.actionProposalId,
        { expected_payload_fingerprint: proposal.payloadFingerprint },
      ),
    refreshTechnicalDebt: props.refreshTechnicalDebt,
  })
  if (result.resource) {
    localApprovals.value.push(toActionApprovalPresentation(result.resource))
  }
  approvalMessage.value = {
    success: '',
    'success-refresh-failed': 'Approval was recorded, but TechnicalDebt details could not be refreshed.',
    conflict: 'The action state changed. The latest persisted state has been loaded.',
    'reconciliation-unresolved': 'The action state changed. The latest persisted state has been loaded.',
    forbidden: 'Approval could not be recorded.',
    error: 'Approval could not be recorded.',
  }[result.status]
  approving.value = false
}

async function execute() {
  const proposal = approvedProposal.value
  if (executing.value || proposal == null || executionAlreadyRecorded.value) return
  executing.value = true
  executionMessage.value = ''
  const result = await submitGovernedMutation({
    mutate: () =>
      executeActionProposal(
        props.presentation.technicalDebtId,
        proposal.actionProposalId,
      ),
    refreshTechnicalDebt: props.refreshTechnicalDebt,
  })
  if (result.resource) {
    localExecutions.value.push(toActionExecutionPresentation(result.resource))
  }
  executionMessage.value = {
    success: '',
    'success-refresh-failed': 'Execution was recorded, but TechnicalDebt details could not be refreshed.',
    conflict: 'The action state changed. The latest persisted state has been loaded.',
    'reconciliation-unresolved': 'The action state changed. The latest persisted state has been loaded.',
    forbidden: 'The backend did not authorize this execution.',
    error: 'The execution request did not complete. Check persisted state before any further action.',
  }[result.status]
  executing.value = false
}

async function verify() {
  const execution = selectedExecution.value
  if (verifying.value || execution == null || !canVerify.value) return
  verifying.value = true
  verificationMessage.value = ''
  const result = await submitGovernedMutation({
    mutate: () =>
      verifyActionExecution(
        props.presentation.technicalDebtId,
        execution.actionProposalId,
        execution.actionExecutionId,
      ),
    refreshTechnicalDebt: props.refreshTechnicalDebt,
    recognizeReconciliationConflict: true,
  })
  if (result.resource) {
    localVerifications.value.push(toActionVerificationPresentation(result.resource))
  }
  verificationMessage.value = {
    success: '',
    'success-refresh-failed': 'Verification was recorded, but TechnicalDebt details could not be refreshed.',
    conflict: 'The action state changed. The latest persisted state has been loaded.',
    'reconciliation-unresolved': 'External action could not yet be reconciled. Do not retry the write.',
    forbidden: 'Verification is currently unavailable.',
    error: 'The external action could not be verified.',
  }[result.status]
  verifying.value = false
}
</script>

<template>
  <section class="governance-workbench" aria-labelledby="governance-workbench-heading">
    <header class="governance-workbench__header">
      <p class="governance-stage__eyebrow">L4 action workbench</p>
      <h2 id="governance-workbench-heading">Governed External Action</h2>
      <p>Human approves. Policy authorizes. Executor performs. Verification checks.</p>
    </header>

    <section class="governance-stage" aria-labelledby="action-approval-heading">
      <header class="governance-stage__header">
        <p class="governance-stage__eyebrow">Approved</p>
        <h2 id="action-approval-heading">L4 Human Approval</h2>
        <p>A human approves the exact immutable payload. Approval is not policy authorization.</p>
      </header>
      <div v-if="recordedApproval" class="governance-record">
        <strong>Approved</strong>
        <dl class="candidate-fact-list">
          <div><dt>Proposal ID</dt><dd class="candidate-breakable">{{ recordedApproval.actionProposalId }}</dd></div>
          <div><dt>Actor reference</dt><dd class="candidate-breakable">{{ recordedApproval.actorReference }}</dd></div>
          <div><dt>Timestamp</dt><dd><time :datetime="recordedApproval.createdAt">{{ formatDisplayTimestamp(recordedApproval.createdAt) }}</time></dd></div>
          <div><dt>Payload fingerprint</dt><dd class="candidate-breakable">{{ recordedApproval.payloadFingerprint }}</dd></div>
        </dl>
      </div>
      <p v-else class="candidate-empty-inline">No human L4 approval has been recorded.</p>
      <p v-if="currentPreview && recordedApproval && !currentPreviewApproval" class="governance-notice">
        The recorded approval belongs to an earlier proposal. The current preview is not described as approved.
      </p>
      <p class="technical-debt-detail-actions">
        <button type="button" class="button button--approval" :disabled="approving || !currentPreview || !!currentPreviewApproval" @click="approve">
          {{ approving ? 'Approving…' : 'Approve External Action' }}
        </button>
      </p>
      <p v-if="approvalMessage" class="candidate-detail-message" role="alert">{{ approvalMessage }}</p>
    </section>

    <section class="governance-stage" aria-labelledby="action-execution-heading">
      <header class="governance-stage__header">
        <p class="governance-stage__eyebrow">Executed</p>
        <h2 id="action-execution-heading">Execution</h2>
        <p>The governed executor attempts the approved action only after backend policy evaluation.</p>
      </header>
      <p class="governance-write-boundary">
        This action may create a real GitHub Issue when the backend execution plane is enabled and configured.
      </p>
      <div v-if="selectedExecution" class="governance-record">
        <p class="governance-status" :data-status="selectedExecution.status">{{ selectedExecution.status }}</p>
        <p v-if="selectedExecution.status === 'UNKNOWN'" class="governance-notice">
          External outcome is uncertain. Do not retry the write. Use verification/reconciliation.
        </p>
        <p v-else-if="selectedExecution.status === 'FAILED'" class="governance-notice">
          This attempt definitely failed. A new ActionProposal is required for a new attempt.
        </p>
        <dl class="candidate-fact-list">
          <div><dt>Execution ID</dt><dd class="candidate-breakable">{{ selectedExecution.actionExecutionId }}</dd></div>
          <div><dt>Proposal ID</dt><dd class="candidate-breakable">{{ selectedExecution.actionProposalId }}</dd></div>
          <div><dt>Started</dt><dd><time :datetime="selectedExecution.startedAt">{{ formatDisplayTimestamp(selectedExecution.startedAt) }}</time></dd></div>
          <div v-if="selectedExecution.completedAt"><dt>Completed</dt><dd><time :datetime="selectedExecution.completedAt">{{ formatDisplayTimestamp(selectedExecution.completedAt) }}</time></dd></div>
          <div v-if="selectedExecution.safeErrorCategory"><dt>Safe outcome category</dt><dd>{{ selectedExecution.safeErrorCategory }}</dd></div>
        </dl>
      </div>
      <p v-else class="candidate-empty-inline">No execution attempt has been recorded.</p>
      <p class="technical-debt-detail-actions">
        <button type="button" class="button" :disabled="executing || !approvedProposal || executionAlreadyRecorded" @click="execute">
          {{ executing ? 'Executing…' : 'Execute Approved Action' }}
        </button>
      </p>
      <p v-if="executionMessage" class="candidate-detail-message" role="alert">{{ executionMessage }}</p>
    </section>

    <section class="governance-stage" aria-labelledby="external-reference-heading">
      <header class="governance-stage__header">
        <p class="governance-stage__eyebrow">External reference</p>
        <h2 id="external-reference-heading">External Reference</h2>
      </header>
      <p v-if="selectedExecution?.externalIssueUrl" class="governance-external-reference">
        <a :href="selectedExecution.externalIssueUrl" target="_blank" rel="noopener noreferrer">
          Open persisted GitHub Issue<span v-if="selectedExecution.externalIssueNumber"> #{{ selectedExecution.externalIssueNumber }}</span>
        </a>
      </p>
      <p v-else class="candidate-empty-inline">No external reference has been persisted.</p>
    </section>

    <section class="governance-stage" aria-labelledby="action-verification-heading">
      <header class="governance-stage__header">
        <p class="governance-stage__eyebrow">Verified</p>
        <h2 id="action-verification-heading">Verification</h2>
        <p>Independent read-back checks external truth. It does not change TechnicalDebt lifecycle.</p>
      </header>
      <div v-if="selectedVerification" class="governance-record">
        <p class="governance-status" :data-status="selectedVerification.result">{{ selectedVerification.result }}</p>
        <p v-if="selectedVerification.result === 'PASS'">The external issue matches the approved proposal.</p>
        <p v-else-if="selectedVerification.result === 'FAIL'">Read-back completed, but the approved semantics differ.</p>
        <p v-else>Verification could not currently complete.</p>
        <dl class="candidate-fact-list">
          <div><dt>Verification ID</dt><dd class="candidate-breakable">{{ selectedVerification.actionVerificationId }}</dd></div>
          <div v-if="selectedVerification.safeReasonCode"><dt>Safe reason</dt><dd>{{ selectedVerification.safeReasonCode }}</dd></div>
          <div><dt>Timestamp</dt><dd><time :datetime="selectedVerification.createdAt">{{ formatDisplayTimestamp(selectedVerification.createdAt) }}</time></dd></div>
        </dl>
      </div>
      <p v-else class="candidate-empty-inline">No verification result has been recorded.</p>
      <p class="technical-debt-detail-actions">
        <button type="button" class="button button--secondary" :disabled="verifying || !canVerify" @click="verify">
          {{ verifying ? 'Verifying…' : 'Verify External Action' }}
        </button>
      </p>
      <p v-if="verificationMessage" class="candidate-detail-message" role="alert">{{ verificationMessage }}</p>
    </section>

    <TechnicalDebtAuditTrail
      :technical-debt-id="presentation.technicalDebtId"
      :technical-debt-created-at="presentation.createdAt"
      :action-proposals="presentation.actionProposals"
      :action-approvals="approvals"
      :action-policy-decisions="presentation.actionPolicyDecisions"
      :action-executions="executions"
      :action-verifications="verifications"
    />
  </section>
</template>
