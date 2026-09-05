<script setup lang="ts">
import type { PolicyDecisionItem } from '~/types/agentRun'

defineProps<{
  decisions: PolicyDecisionItem[]
}>()
</script>

<template>
  <section
    class="candidate-detail-section"
    aria-labelledby="candidate-policy-trace-heading"
  >
    <h3 id="candidate-policy-trace-heading">Policy trace</h3>
    <p class="candidate-section-introduction">
      Runtime policy decisions for tool execution. Policy ALLOW is not human approval.
    </p>
    <p v-if="decisions.length === 0" class="candidate-section-introduction">
      No policy decisions were recorded.
    </p>
    <div v-else class="candidate-table-wrapper">
      <table class="candidate-table investigation-trace-table">
        <caption class="visually-hidden">Policy decision trace</caption>
        <thead>
          <tr>
            <th scope="col">Decision</th>
            <th scope="col">Requested effect</th>
            <th scope="col">Requested risk</th>
            <th scope="col">Required scopes</th>
            <th scope="col">Rule</th>
            <th scope="col">Reason</th>
            <th scope="col">Decided at</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="decision in decisions" :key="`${decision.toolExecutionId}:${decision.decidedAt}`">
            <th scope="row">
              <span class="candidate-title">{{ decision.decisionLabel }}</span>
              <span class="candidate-identifier">{{ decision.decision }}</span>
            </th>
            <td>{{ decision.requestedEffect }}</td>
            <td>{{ decision.requestedRisk }}</td>
            <td>{{ decision.requiredScopes.join(', ') }}</td>
            <td class="candidate-breakable">{{ decision.ruleId }}</td>
            <td class="candidate-breakable">{{ decision.reasonCode }}</td>
            <td>{{ decision.decidedAt }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
