<script setup lang="ts">
import {
  implementedSignalSources,
  implementedSignalSourcesCapabilityLabel,
  implementedSignalSourcesHeading,
  implementedSignalSourcesNote,
} from '~/utils/implementedSignalSources'
</script>

<template>
  <section class="overview-section" aria-labelledby="overview-sources-heading">
    <header class="overview-section-header">
      <h2 id="overview-sources-heading">{{ implementedSignalSourcesHeading }}</h2>
      <p class="overview-kicker">{{ implementedSignalSourcesCapabilityLabel }}</p>
      <p class="overview-section-note">{{ implementedSignalSourcesNote }}</p>
    </header>

    <ul class="overview-source-list">
      <li v-for="source in implementedSignalSources" :key="source.id">
        <p class="overview-source-name">{{ source.name }}</p>
        <p class="overview-source-copy">{{ source.description }}</p>
      </li>
    </ul>
  </section>
</template>
