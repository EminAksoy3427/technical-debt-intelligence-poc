<script setup lang="ts">
import type { ToolExecutionItem } from '~/types/agentRun'

defineProps<{
  executions: ToolExecutionItem[]
}>()
</script>

<template>
  <section
    class="candidate-detail-section"
    aria-labelledby="candidate-tool-trace-heading"
  >
    <h3 id="candidate-tool-trace-heading">Tool trace</h3>
    <p class="candidate-section-introduction">
      Recorded tool executions for this investigation. Tool availability is not permission.
    </p>
    <p v-if="executions.length === 0" class="candidate-section-introduction">
      No tool executions were recorded.
    </p>
    <div v-else class="candidate-table-wrapper">
      <table class="candidate-table investigation-trace-table">
        <caption class="visually-hidden">Tool execution trace</caption>
        <thead>
          <tr>
            <th scope="col">Sequence</th>
            <th scope="col">Tool</th>
            <th scope="col">Version</th>
            <th scope="col">Status</th>
            <th scope="col">Duration</th>
            <th scope="col">Safe error</th>
            <th scope="col">Result references</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="execution in executions" :key="execution.toolExecutionId">
            <td>{{ execution.sequenceNumber }}</td>
            <th scope="row">
              <span class="candidate-title">{{ execution.toolId }}</span>
              <span class="candidate-identifier">{{ execution.toolExecutionId }}</span>
            </th>
            <td>{{ execution.toolVersion }}</td>
            <td>
              <span class="badge badge--neutral">{{ execution.statusLabel }}</span>
            </td>
            <td>{{ execution.durationMs }} ms</td>
            <td>
              <span v-if="execution.errorCode != null || execution.errorMessage != null">
                <span v-if="execution.errorCode != null">{{ execution.errorCode }}</span>
                <span
                  v-if="execution.errorMessage != null"
                  class="candidate-identifier"
                >{{ execution.errorMessage }}</span>
              </span>
            </td>
            <td>
              <ul
                v-if="execution.resultReferences.length > 0"
                class="candidate-investigation-note-list"
              >
                <li
                  v-for="reference in execution.resultReferences"
                  :key="reference.key"
                >
                  <span class="badge badge--neutral">{{ reference.referenceTypeLabel }}</span>
                  <span class="candidate-identifier candidate-breakable">{{
                    reference.identifier
                  }}</span>
                  <span v-if="reference.relatedLabel != null">{{ reference.relatedLabel }}</span>
                </li>
              </ul>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
