<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'

defineProps<{
  evidence: CandidateEvidenceItem[]
}>()
</script>

<template>
  <section
    class="candidate-snapshot candidate-evidence-section"
    aria-labelledby="candidate-evidence-heading"
  >
    <h2 id="candidate-evidence-heading">Evidence</h2>
    <p v-if="evidence.length === 0" class="candidate-empty-inline">
      No evidence is included.
    </p>
    <ul v-else class="candidate-record-list">
      <li v-for="item in evidence" :key="item.evidenceId">
        <CandidateEvidenceItem :item="item" />
      </li>
    </ul>
  </section>
</template>
