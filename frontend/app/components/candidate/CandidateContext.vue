<script setup lang="ts">
import type { CandidateContextSummary } from '~/types/candidate'

defineProps<{
  context: CandidateContextSummary
}>()
</script>

<template>
  <section class="candidate-detail-section" aria-labelledby="candidate-context-heading">
    <h2 id="candidate-context-heading">Context</h2>
    <dl class="candidate-detail-list">
      <div>
        <dt>Asset criticality</dt>
        <dd class="candidate-criticality">{{ context.assetCriticality }}</dd>
      </div>
      <div>
        <dt>Dependency summary</dt>
        <dd>{{ context.dependencySummary }}</dd>
      </div>
    </dl>
    <p class="candidate-context-note">Asset criticality provides context; it is not technical-debt risk.</p>
  </section>
</template>
