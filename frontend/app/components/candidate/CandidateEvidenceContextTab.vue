<script setup lang="ts">
import type { CandidateDetailPresentation } from '~/types/candidate'

defineProps<{
  presentation: CandidateDetailPresentation
}>()
</script>

<template>
  <div class="candidate-evidence-layout">
    <div class="candidate-evidence-primary">
      <div class="candidate-section-surface">
        <CandidateEvidenceList :evidence="presentation.evidence" />
      </div>
      <div class="candidate-section-surface">
        <CandidateSignalList :signals="presentation.signals" />
      </div>
    </div>
    <div class="candidate-section-surface">
      <CandidateEnterpriseContext
        :asset="presentation.enterpriseContext.asset"
        :ownerships="presentation.enterpriseContext.ownerships"
        :relationships="presentation.enterpriseContext.relationships"
        :incidents="presentation.enterpriseContext.incidents"
      />
    </div>
    <div class="candidate-section-surface">
      <CandidateDependencyContext :dependency-context="presentation.dependencyContext" />
    </div>
  </div>
</template>
