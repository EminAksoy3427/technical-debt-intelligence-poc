<script setup lang="ts">
interface PrimaryNavigationItem {
  to: string
  label: string
}

// Implemented workspaces only. Add a route here when that workspace exists.
const primaryNavigationItems: readonly PrimaryNavigationItem[] = [
  { to: '/candidates', label: 'Candidates' },
  { to: '/sources', label: 'Sources & Connectors' },
]
</script>

<template>
  <header class="application-header">
    <div class="application-header-inner">
      <NuxtLink to="/candidates" class="application-identity">
        <span class="application-mark" aria-hidden="true" />
        <span class="application-identity-text">
          <span class="application-name">Technical Debt Intelligence</span>
          <span class="application-context">Governance</span>
        </span>
      </NuxtLink>

      <nav class="application-navigation" aria-label="Primary navigation">
        <ul class="navigation-list">
          <li v-for="item in primaryNavigationItems" :key="item.to">
            <NuxtLink :to="item.to" class="navigation-link">
              {{ item.label }}
            </NuxtLink>
          </li>
        </ul>
      </nav>
    </div>
  </header>
</template>
