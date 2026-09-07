<script setup lang="ts">
import {
  sourceIngestionCapabilities,
  sourceIngestionCapabilitiesHeading,
  sourceIngestionCapabilitiesNote,
} from '~/utils/sourceIngestionCapabilities'
</script>

<template>
  <section class="sources-section" aria-labelledby="sources-ingestion-heading">
    <header class="sources-section-header">
      <h2 id="sources-ingestion-heading">{{ sourceIngestionCapabilitiesHeading }}</h2>
      <p class="sources-section-note">{{ sourceIngestionCapabilitiesNote }}</p>
    </header>

    <ul class="sources-capability-list">
      <li
        v-for="capability in sourceIngestionCapabilities"
        :key="capability.id"
        class="sources-capability-item"
      >
        <h3 class="sources-capability-name">{{ capability.name }}</h3>
        <p class="sources-capability-kind">{{ capability.observationKind }}</p>
        <p class="sources-capability-role">
          <span class="visually-hidden">Normalized role: </span>{{ capability.normalizedRole }}
        </p>
        <p class="sources-capability-copy">{{ capability.explanation }}</p>
      </li>
    </ul>
  </section>
</template>
