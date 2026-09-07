<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'
import {
  formatDisplayTimestamp,
  formatEvidenceFinding,
  formatSourceSystemLabel,
} from '~/utils/candidateDetailDisplay'

const props = defineProps<{
  item: CandidateEvidenceItem
}>()

function httpReferenceHref(referenceUri: string): string | undefined {
  return /^https?:\/\//i.test(referenceUri) ? referenceUri : undefined
}

const finding = computed(() => formatEvidenceFinding(props.item.sourceReference))
const httpHref = computed(() =>
  props.item.referenceUri == null ? undefined : httpReferenceHref(props.item.referenceUri),
)

const provenanceRows = computed(() => {
  const rows = [
    { label: 'Evidence ID', value: props.item.evidenceId },
    { label: 'Source reference', value: props.item.sourceReference },
    { label: 'Captured at (raw)', value: props.item.capturedAt },
    { label: 'Captured', value: formatDisplayTimestamp(props.item.capturedAt) },
  ]
  if (props.item.referenceUri != null && httpHref.value == null) {
    rows.push({ label: 'Reference URI', value: props.item.referenceUri })
  }
  return rows
})
</script>

<template>
  <article class="candidate-record">
    <p class="candidate-record-kicker">
      <span class="visually-hidden">Source </span>{{ formatSourceSystemLabel(item.sourceSystem) }}
    </p>
    <p v-if="finding.location" class="candidate-record-location">{{ finding.location }}</p>
    <p class="candidate-record-body">{{ finding.summary }}</p>
    <p v-if="httpHref" class="candidate-record-link">
      <a
        class="candidate-reference-link"
        :href="httpHref"
        rel="noopener noreferrer"
        target="_blank"
      >
        {{ item.referenceUri }}
        <span class="visually-hidden">(opens in a new tab)</span>
      </a>
    </p>
    <CandidateProvenanceDetails :rows="provenanceRows" />
  </article>
</template>
