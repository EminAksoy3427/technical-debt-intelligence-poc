<script setup lang="ts">
import { formatDisplayTimestamp } from '~/utils/candidateDetailDisplay'
import { buildTechnicalDebtAuditTimeline } from '~/utils/technicalDebtAudit'
import type {
  ActionApprovalPresentation,
  ActionExecutionPresentation,
  ActionPolicyDecisionPresentation,
  ActionProposalPresentation,
  ActionVerificationPresentation,
} from '~/types/technicalDebt'

const props = defineProps<{
  technicalDebtId: string
  technicalDebtCreatedAt: string
  actionProposals: readonly ActionProposalPresentation[]
  actionApprovals: readonly ActionApprovalPresentation[]
  actionPolicyDecisions: readonly ActionPolicyDecisionPresentation[]
  actionExecutions: readonly ActionExecutionPresentation[]
  actionVerifications: readonly ActionVerificationPresentation[]
}>()

const items = computed(() => buildTechnicalDebtAuditTimeline(props))
</script>

<template>
  <section class="governance-stage governance-audit" aria-labelledby="technical-debt-audit-heading">
    <header class="governance-stage__header">
      <p class="governance-stage__eyebrow">Audit</p>
      <h2 id="technical-debt-audit-heading">Audit Trail</h2>
      <p>Persisted record of the governance chain. Verification does not close this debt.</p>
    </header>
    <ol class="governance-timeline">
      <li v-for="item in items" :key="`${item.type}:${item.id}`">
        <span class="governance-timeline__marker" aria-hidden="true"></span>
        <div>
          <strong>{{ item.label }}</strong>
          <p v-if="item.relationship" class="governance-record-reference">
            {{ item.relationship }}
          </p>
          <time :datetime="item.timestamp">{{ formatDisplayTimestamp(item.timestamp) }}</time>
        </div>
      </li>
    </ol>
  </section>
</template>
