<script setup lang="ts">
import type {
  CandidateDetailCore,
  CandidateEvidenceItem,
  CandidateSignalItem,
} from '~/types/candidate'
import {
  formatSourceSystemLabel,
  uniqueSourceSystems,
} from '~/utils/candidateDetailDisplay'

const props = defineProps<{
  problemLabel: string
  candidate: CandidateDetailCore
  signals: CandidateSignalItem[]
  evidence: CandidateEvidenceItem[]
}>()

const sourceSystems = computed(() => uniqueSourceSystems(props.signals, props.evidence))
</script>

<template>
  <section class="candidate-summary-block" aria-labelledby="candidate-summary-heading">
    <h2 id="candidate-summary-heading">Candidate summary</h2>

    <div class="candidate-summary-primary">
      <div>
        <p class="candidate-kv-label">Problem</p>
        <p class="candidate-summary-problem">{{ problemLabel }}</p>
      </div>
      <div>
        <p class="candidate-kv-label">Affected asset</p>
        <p class="candidate-summary-asset">{{ candidate.assetDisplayName }}</p>
      </div>
    </div>

    <dl class="candidate-metric-row">
      <div v-if="sourceSystems.length > 0" class="candidate-metric">
        <dt>Source</dt>
        <dd>{{ sourceSystems.map(formatSourceSystemLabel).join(', ') }}</dd>
      </div>
      <div class="candidate-metric">
        <dt>Signals</dt>
        <dd>{{ signals.length }}</dd>
      </div>
      <div class="candidate-metric">
        <dt>Evidence</dt>
        <dd>{{ evidence.length }}</dd>
      </div>
    </dl>
  </section>
</template>
