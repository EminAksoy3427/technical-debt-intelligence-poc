<script setup lang="ts">
import {
  candidatePoolAssetTypeLabels,
  type CandidateSignalItem,
} from '~/types/candidate'
import {
  formatDisplayTimestamp,
  formatSeverityLabel,
  formatSourceSystemLabel,
} from '~/utils/candidateDetailDisplay'
import { candidateProblemTypeDisplayLabel } from '~/utils/resolveCandidatePresentationTitle'

const props = defineProps<{
  signal: CandidateSignalItem
}>()

const displayType = computed(() => candidateProblemTypeDisplayLabel(props.signal.signalType))

const provenanceRows = computed(() => {
  const rows = [
    { label: 'Signal ID', value: props.signal.signalId },
    { label: 'Signal type', value: props.signal.signalType },
    { label: 'Source record ID', value: props.signal.sourceRecordId },
    { label: 'Detected at (raw)', value: props.signal.detectedAt },
    { label: 'Detected', value: formatDisplayTimestamp(props.signal.detectedAt) },
    { label: 'Canonical asset key', value: props.signal.affectedAssetKey },
  ]
  return rows
})
</script>

<template>
  <article class="candidate-record">
    <p class="candidate-record-kicker">
      {{ formatSourceSystemLabel(signal.sourceSystem) }}
      <template v-if="signal.severity != null">
        <span aria-hidden="true"> · </span>
        {{ formatSeverityLabel(signal.severity) }}
      </template>
    </p>
    <p class="candidate-record-title">
      <span class="visually-hidden">Signal type </span>{{ displayType }}
    </p>
    <p class="candidate-record-location">
      <span class="candidate-breakable">{{ signal.affectedAssetKey }}</span>
      <span class="candidate-type-badge">{{
        candidatePoolAssetTypeLabels[signal.affectedAssetType]
      }}</span>
    </p>
    <CandidateProvenanceDetails :rows="provenanceRows" />
  </article>
</template>
