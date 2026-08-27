<script setup lang="ts">
import type { CandidateEvidenceItem } from '~/types/candidate'

defineProps<{
  evidence: CandidateEvidenceItem[]
}>()
</script>

<template>
  <section class="candidate-detail-section" aria-labelledby="candidate-evidence-heading">
    <h2 id="candidate-evidence-heading">Supporting evidence</h2>
    <p class="candidate-section-introduction">
      Evidence supports Candidate review; it does not validate the Candidate.
    </p>
    <ul class="candidate-evidence-list">
      <li v-for="item in evidence" :key="item.id">
        <p class="candidate-evidence-source">{{ item.sourceLabel }}</p>
        <p class="candidate-evidence-summary">{{ item.summary }}</p>
        <span class="candidate-evidence-id">{{ item.id }}</span>
      </li>
    </ul>
  </section>
</template>
