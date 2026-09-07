<script setup lang="ts">
defineProps<{
  correlationRationale: string
}>()
</script>

<template>
  <section class="candidate-correlation" aria-labelledby="candidate-correlation-heading">
    <h2 id="candidate-correlation-heading">Correlation explanation</h2>
    <p class="candidate-helper">System-generated correlation, not validation.</p>
    <p class="candidate-correlation-rationale">{{ correlationRationale }}</p>
  </section>
</template>
