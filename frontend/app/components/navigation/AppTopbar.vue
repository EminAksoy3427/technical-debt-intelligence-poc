<script setup lang="ts">
import { resolveAppShellContext } from '~/utils/appShellNavigation'

defineProps<{
  navigationOpen: boolean
}>()

defineEmits<{
  toggleNavigation: []
}>()

const route = useRoute()

const shellContext = computed(() => resolveAppShellContext(route.path))
</script>

<template>
  <header class="app-topbar">
    <div class="app-topbar-start">
      <button
        type="button"
        class="app-topbar-menu"
        :aria-expanded="navigationOpen"
        aria-controls="app-sidebar"
        @click="$emit('toggleNavigation')"
      >
        <span class="visually-hidden">{{ navigationOpen ? 'Close navigation' : 'Open navigation' }}</span>
        <svg class="app-topbar-menu-icon" viewBox="0 0 24 24" aria-hidden="true">
          <path d="M4 7h16M4 12h16M4 17h16" />
        </svg>
      </button>

      <p class="app-topbar-context">{{ shellContext.sectionLabel }}</p>
    </div>

    <p class="app-topbar-environment">PoC</p>
  </header>
</template>
