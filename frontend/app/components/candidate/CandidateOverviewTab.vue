<script setup lang="ts">
import type { CandidateDetailPresentation } from '~/types/candidate'

defineProps<{
  presentation: CandidateDetailPresentation
  problemLabel: string
}>()

const emit = defineEmits<{
  selectInvestigation: []
}>()
</script>

<template>
  <div class="candidate-overview-layout">
    <div class="candidate-section-surface">
      <CandidateSummaryCard
        :problem-label="problemLabel"
        :candidate="presentation.candidate"
        :signals="presentation.signals"
        :evidence="presentation.evidence"
      />
      <CandidateCorrelationSummary :correlation-rationale="presentation.candidate.correlationRationale" />
    </div>

    <div class="candidate-overview-snapshots">
      <div class="candidate-section-surface">
        <CandidateEnterpriseSnapshot
          :asset="presentation.enterpriseContext.asset"
          :ownerships="presentation.enterpriseContext.ownerships"
        />
      </div>
      <div class="candidate-section-surface">
        <CandidateDependencySummary :dependency-context="presentation.dependencyContext" />
      </div>
    </div>

    <section class="candidate-next-step" aria-labelledby="candidate-next-step-heading">
      <h2 id="candidate-next-step-heading">Next step</h2>
      <p class="candidate-helper">
        Use AI Investigation to analyze the recorded evidence and enterprise context.
      </p>
      <button type="button" class="button" @click="emit('selectInvestigation')">
        Open AI Investigation
      </button>
    </section>
  </div>
</template>
