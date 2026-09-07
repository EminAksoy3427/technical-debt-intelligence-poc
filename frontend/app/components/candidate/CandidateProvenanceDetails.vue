<script setup lang="ts">
withDefaults(
  defineProps<{
    rows: readonly { label: string; value: string }[]
    summaryLabel?: string
  }>(),
  {
    summaryLabel: 'Technical details',
  },
)
</script>

<template>
  <details v-if="rows.length > 0" class="candidate-disclosure">
    <summary>{{ summaryLabel }}</summary>
    <dl class="candidate-kv-list candidate-kv-list--compact">
      <div v-for="row in rows" :key="row.label" class="candidate-kv-row">
        <dt>{{ row.label }}</dt>
        <dd class="candidate-identifier candidate-breakable">{{ row.value }}</dd>
      </div>
    </dl>
  </details>
</template>
