<script setup lang="ts">
import {
  overviewOperatingModelHeading,
  overviewOperatingModelNote,
  overviewOperatingModelStages,
} from '~/utils/overviewOperatingModel'
</script>

<template>
  <section class="overview-section" aria-labelledby="overview-workflow-heading">
    <header class="overview-section-header">
      <h2 id="overview-workflow-heading">{{ overviewOperatingModelHeading }}</h2>
      <p class="overview-section-note">{{ overviewOperatingModelNote }}</p>
    </header>

    <ol class="overview-workflow">
      <li
        v-for="(stage, index) in overviewOperatingModelStages"
        :key="stage.id"
        class="overview-workflow-stage"
        :class="{
          'overview-workflow-stage--branch': index >= 3,
        }"
      >
        <p class="overview-workflow-name">
          <span class="overview-workflow-index" aria-hidden="true">{{ index + 1 }}</span>
          {{ stage.name }}
        </p>
        <p class="overview-workflow-copy">{{ stage.description }}</p>
      </li>
    </ol>
  </section>
</template>
