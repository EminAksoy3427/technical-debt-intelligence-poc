<script setup lang="ts">
import type { CandidateSignalItem } from '~/types/candidate'

defineProps<{
  signals: CandidateSignalItem[]
}>()
</script>

<template>
  <section
    class="candidate-snapshot candidate-signal-section"
    aria-labelledby="candidate-signals-heading"
  >
    <h2 id="candidate-signals-heading">Signals</h2>
    <p v-if="signals.length === 0" class="candidate-empty-inline">
      No signals are included.
    </p>
    <ul v-else class="candidate-record-list">
      <li v-for="signal in signals" :key="signal.signalId">
        <CandidateSignalItem :signal="signal" />
      </li>
    </ul>
  </section>
</template>
