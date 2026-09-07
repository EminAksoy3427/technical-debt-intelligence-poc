<script setup lang="ts">
import {
  candidateDetailTabs,
  type CandidateDetailTabId,
} from '~/utils/candidateDetailTabs'

const props = defineProps<{
  selectedTab: CandidateDetailTabId
}>()

const emit = defineEmits<{
  select: [tab: CandidateDetailTabId]
}>()

const tablistRef = ref<HTMLElement | null>(null)

function selectedIndex(): number {
  return candidateDetailTabs.findIndex((tab) => tab.id === props.selectedTab)
}

function activateIndex(index: number): void {
  const tab = candidateDetailTabs[index]
  if (tab == null) {
    return
  }

  emit('select', tab.id)
  nextTick(() => {
    const buttons = tablistRef.value?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
    buttons?.[index]?.focus()
  })
}

function onKeydown(event: KeyboardEvent): void {
  const current = selectedIndex()
  if (current < 0) {
    return
  }

  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    event.preventDefault()
    activateIndex((current + 1) % candidateDetailTabs.length)
    return
  }

  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    event.preventDefault()
    activateIndex((current - 1 + candidateDetailTabs.length) % candidateDetailTabs.length)
    return
  }

  if (event.key === 'Home') {
    event.preventDefault()
    activateIndex(0)
    return
  }

  if (event.key === 'End') {
    event.preventDefault()
    activateIndex(candidateDetailTabs.length - 1)
  }
}
</script>

<template>
  <div
    ref="tablistRef"
    class="candidate-detail-tablist"
    role="tablist"
    aria-label="Candidate detail"
    @keydown="onKeydown"
  >
    <button
      v-for="tab in candidateDetailTabs"
      :id="tab.tabId"
      :key="tab.id"
      type="button"
      class="candidate-detail-tab"
      role="tab"
      :aria-selected="selectedTab === tab.id"
      :aria-controls="tab.panelId"
      :tabindex="selectedTab === tab.id ? 0 : -1"
      @click="emit('select', tab.id)"
    >
      {{ tab.label }}
    </button>
  </div>
</template>
