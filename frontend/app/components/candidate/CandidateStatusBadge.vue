<script setup lang="ts">
import type { CandidateReviewStatus } from '~/types/candidate'

const props = defineProps<{
  status: CandidateReviewStatus
}>()

const statusLabels: Record<CandidateReviewStatus, string> = {
  awaiting_review: 'Awaiting review',
  needs_information: 'Needs information',
}
</script>

<template>
  <span class="status-badge" :class="`status-badge--${props.status}`">
    {{ statusLabels[props.status] }}
  </span>
</template>
