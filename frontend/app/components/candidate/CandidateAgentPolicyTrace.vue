<script setup lang="ts">
import type { PolicyDecisionItem } from '~/types/agentRun'

defineProps<{
  decisions: PolicyDecisionItem[]
}>()

function decisionProvenanceRows(decision: PolicyDecisionItem): { label: string; value: string }[] {
  const rows = [
    { label: 'Decision', value: decision.decision },
    { label: 'Decision summary', value: decision.decisionLabel },
    { label: 'Tool execution ID', value: decision.toolExecutionId },
    { label: 'Requested effect', value: decision.requestedEffect },
    { label: 'Requested risk', value: decision.requestedRisk },
    { label: 'Rule', value: decision.ruleId },
    { label: 'Reason', value: decision.reasonCode },
    { label: 'Decided at (raw)', value: decision.decidedAt },
  ]
  if (decision.toolId != null) {
    rows.push({ label: 'Tool', value: decision.toolId })
  }
  if (decision.requiredScopes.length > 0) {
    rows.push({ label: 'Required scopes', value: decision.requiredScopes.join(', ') })
  }
  return rows
}

function policyExplanation(decision: PolicyDecisionItem): string {
  if (decision.decision === 'ALLOW') {
    return 'Runtime policy allowed this tool execution.'
  }
  return 'Runtime policy denied this tool execution.'
}
</script>

<template>
  <section
    class="candidate-investigation-trace"
    aria-labelledby="candidate-policy-trace-heading"
  >
    <h4 id="candidate-policy-trace-heading">Policy decisions</h4>
    <p class="candidate-helper">
      Runtime policy decisions govern tool execution. Policy ALLOW is not human approval.
    </p>
    <p v-if="decisions.length === 0" class="candidate-empty-value">
      No policy decisions were recorded.
    </p>
    <ul v-else class="candidate-trace-list">
      <li
        v-for="decision in decisions"
        :key="`${decision.toolExecutionId}:${decision.decidedAt}`"
        class="candidate-trace-item"
      >
        <div class="candidate-trace-primary">
          <span class="badge badge--neutral">{{ decision.decisionStatusLabel }}</span>
          <span v-if="decision.toolDisplayLabel" class="candidate-trace-title">
            {{ decision.toolDisplayLabel }}
          </span>
        </div>
        <p class="candidate-helper">{{ policyExplanation(decision) }}</p>
        <p class="candidate-record-meta">
          Requested effect: {{ decision.requestedEffectLabel }}
          · Requested risk: {{ decision.requestedRiskLabel }}
        </p>
        <CandidateProvenanceDetails
          summary-label="Technical details"
          :rows="decisionProvenanceRows(decision)"
        />
      </li>
    </ul>
  </section>
</template>
