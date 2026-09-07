<script setup lang="ts">
import {
  appShellPrimaryNavigation,
  isAppShellNavItemActive,
  type AppShellNavItem,
} from '~/utils/appShellNavigation'

defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  close: []
}>()

const route = useRoute()

const sidebarIcons: Record<AppShellNavItem['id'], string> = {
  overview:
    'M4 4h7v8H4V4zm9 0h7v5h-7V4zm0 8h7v8h-7v-8zM4 15h7v5H4v-5z',
  candidates:
    'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
  'technical-debts':
    'M9 11l2 2 4-4M6 4h9l3 3v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z',
  sources:
    'M4 6c0-1.1 3.6-2 8-2s8 .9 8 2-3.6 2-8 2-8-.9-8-2zm0 6c0-1.1 3.6-2 8-2s8 .9 8 2M4 6v12c0 1.1 3.6 2 8 2s8-.9 8-2V6',
}

function isLinkActive(to: string): boolean {
  return isAppShellNavItemActive(route.path, to)
}
</script>

<template>
  <aside
    id="app-sidebar"
    class="app-sidebar"
    :class="{ 'app-sidebar--open': open }"
    aria-label="Application"
  >
    <NuxtLink v-slot="{ href, navigate }" to="/overview" custom>
      <a :href="href" class="app-sidebar-brand" @click="(event) => { navigate(event); emit('close') }">
        <span class="app-sidebar-brand-name">TechDebt IQ</span>
        <span class="app-sidebar-brand-subtitle">Intelligence &amp; Governance</span>
      </a>
    </NuxtLink>

    <nav class="app-sidebar-nav" aria-label="Primary">
      <ul class="app-sidebar-list">
        <li v-for="item in appShellPrimaryNavigation" :key="item.id">
          <NuxtLink
            :to="item.to"
            class="app-sidebar-link"
            :class="{ 'app-sidebar-link--active': isLinkActive(item.to) }"
            :aria-current="isLinkActive(item.to) ? 'page' : undefined"
            @click="emit('close')"
          >
            <svg class="app-sidebar-icon" viewBox="0 0 24 24" aria-hidden="true">
              <path :d="sidebarIcons[item.id]" />
            </svg>
            <span>{{ item.label }}</span>
          </NuxtLink>
        </li>
      </ul>
    </nav>

    <p class="app-sidebar-footer">
      <span class="app-sidebar-footer-title">Proof of concept</span>
      <span class="app-sidebar-footer-copy">Not a production environment</span>
    </p>
  </aside>
</template>
