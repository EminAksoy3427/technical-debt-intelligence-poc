<script setup lang="ts">
import type { GroundingReferenceItem } from '~/types/agentRun'

defineProps<{
  references: GroundingReferenceItem[]
}>()
</script>

<template>
  <div v-if="references.length > 0" class="candidate-grounding-references">
    <p class="candidate-record-kicker">Grounded by</p>
    <ul class="candidate-grounding-list">
      <li v-for="reference in references" :key="reference.key" class="candidate-grounding-item">
        <div class="candidate-grounding-primary">
          <span class="candidate-type-badge">{{ reference.referenceTypeLabel }}</span>
          <span v-if="reference.displayLabel" class="candidate-grounding-label">
            {{ reference.displayLabel }}
          </span>
        </div>
        <CandidateProvenanceDetails
          :summary-label="reference.provenanceSummaryLabel"
          :rows="reference.provenanceRows"
        />
      </li>
    </ul>
  </div>
</template>
