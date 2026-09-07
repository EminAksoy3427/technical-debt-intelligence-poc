<script setup lang="ts">
import {
  sourcesExtensibilityHeading,
  sourcesExtensibilityNote,
  sourcesNormalizationHeading,
  sourcesNormalizationNote,
  sourcesProvenanceHeading,
  sourcesProvenanceNote,
  sourcesSemanticsHeading,
  sourcesSemanticsNotes,
} from '~/utils/sourcesPageCopy'
</script>

<template>
  <section class="sources-section" aria-labelledby="sources-semantics-heading">
    <header class="sources-section-header">
      <h2 id="sources-semantics-heading">{{ sourcesSemanticsHeading }}</h2>
    </header>

    <ul class="sources-semantics-list">
      <li v-for="note in sourcesSemanticsNotes" :key="note">{{ note }}</li>
    </ul>

    <h3 class="sources-subsection-heading">{{ sourcesNormalizationHeading }}</h3>
    <p class="sources-section-copy">{{ sourcesNormalizationNote }}</p>

    <h3 class="sources-subsection-heading">{{ sourcesProvenanceHeading }}</h3>
    <p class="sources-section-copy">{{ sourcesProvenanceNote }}</p>

    <h3 class="sources-subsection-heading">{{ sourcesExtensibilityHeading }}</h3>
    <p class="sources-section-copy">{{ sourcesExtensibilityNote }}</p>
  </section>
</template>
