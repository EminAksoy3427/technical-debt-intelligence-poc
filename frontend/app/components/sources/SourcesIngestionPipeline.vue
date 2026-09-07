<script setup lang="ts">
import {
  sourceIngestionPipelineHeading,
  sourceIngestionPipelineNote,
  sourceIngestionPipelineStages,
} from '~/utils/sourceIngestionPipeline'
</script>

<template>
  <section class="sources-section" aria-labelledby="sources-pipeline-heading">
    <header class="sources-section-header">
      <h2 id="sources-pipeline-heading">{{ sourceIngestionPipelineHeading }}</h2>
      <p class="sources-section-note">{{ sourceIngestionPipelineNote }}</p>
    </header>

    <ol class="sources-pipeline">
      <li
        v-for="(stage, index) in sourceIngestionPipelineStages"
        :key="stage.id"
        class="sources-pipeline-stage"
      >
        <p class="sources-pipeline-name">
          <span class="sources-pipeline-index" aria-hidden="true">{{ index + 1 }}</span>
          {{ stage.name }}
        </p>
        <p class="sources-pipeline-copy">{{ stage.description }}</p>
      </li>
    </ol>
  </section>
</template>
