<script setup lang="ts">
import type { GroundingReferenceItem } from '~/types/agentRun'

defineProps<{
  references: GroundingReferenceItem[]
}>()
</script>

<template>
  <div v-if="references.length > 0" class="candidate-grounding-references">
    <p class="candidate-evidence-id">Grounding references</p>
    <ul class="candidate-investigation-note-list">
      <li v-for="reference in references" :key="reference.key">
        <span class="badge badge--neutral">{{ reference.referenceTypeLabel }}</span>
        <span class="candidate-identifier candidate-breakable">{{ reference.identifier }}</span>
        <span v-if="reference.relatedLabel != null" class="candidate-fact-primary">
          {{ reference.relatedLabel }}
        </span>
      </li>
    </ul>
  </div>
</template>
