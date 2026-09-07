<script setup lang="ts">
import type { ToolExecutionItem } from '~/types/agentRun'

defineProps<{
  executions: ToolExecutionItem[]
}>()

function executionProvenanceRows(execution: ToolExecutionItem): { label: string; value: string }[] {
  const rows = [
    { label: 'Tool', value: execution.toolId },
    { label: 'Tool execution ID', value: execution.toolExecutionId },
    { label: 'Version', value: execution.toolVersion },
    { label: 'Sequence', value: String(execution.sequenceNumber) },
    { label: 'Status', value: execution.status },
  ]
  if (execution.errorCode != null) {
    rows.push({ label: 'Error code', value: execution.errorCode })
  }
  if (execution.errorMessage != null) {
    rows.push({ label: 'Safe error', value: execution.errorMessage })
  }
  for (const [index, reference] of execution.resultReferences.entries()) {
    rows.push({
      label: execution.resultReferences.length === 1 ? 'Result reference' : `Result reference ${index + 1}`,
      value:
        reference.displayLabel == null
          ? `${reference.referenceTypeLabel}: ${reference.identifier}`
          : `${reference.referenceTypeLabel}: ${reference.displayLabel} (${reference.identifier})`,
    })
  }
  return rows
}
</script>

<template>
  <section
    class="candidate-investigation-trace"
    aria-labelledby="candidate-tool-trace-heading"
  >
    <h4 id="candidate-tool-trace-heading">Tool activity</h4>
    <p class="candidate-helper">
      Recorded tool executions for this investigation. Tool availability is not permission.
    </p>
    <p v-if="executions.length === 0" class="candidate-empty-value">
      No tool executions were recorded.
    </p>
    <ol v-else class="candidate-trace-list">
      <li v-for="execution in executions" :key="execution.toolExecutionId" class="candidate-trace-item">
        <div class="candidate-trace-primary">
          <span class="candidate-trace-index">#{{ execution.sequenceNumber }}</span>
          <span class="candidate-trace-title">{{ execution.toolDisplayLabel }}</span>
          <span class="badge badge--neutral">{{ execution.statusLabel }}</span>
          <span class="candidate-trace-duration">{{ execution.durationMs }} ms</span>
        </div>
        <p
          v-if="execution.errorCode != null || execution.errorMessage != null"
          class="candidate-trace-error"
        >
          <span v-if="execution.errorCode != null">{{ execution.errorCode }}</span>
          <span v-if="execution.errorMessage != null">{{ execution.errorMessage }}</span>
        </p>
        <CandidateProvenanceDetails
          summary-label="Technical details"
          :rows="executionProvenanceRows(execution)"
        />
      </li>
    </ol>
  </section>
</template>
