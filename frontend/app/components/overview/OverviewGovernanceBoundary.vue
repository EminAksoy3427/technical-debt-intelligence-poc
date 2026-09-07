<script setup lang="ts">
import {
  overviewGovernanceAiCopy,
  overviewGovernanceAiTitle,
  overviewGovernanceDecisions,
  overviewGovernanceHeading,
  overviewGovernanceHumanCopy,
  overviewGovernanceHumanTitle,
  overviewGovernanceLead,
} from '~/utils/overviewGovernanceCopy'
</script>

<template>
  <section class="overview-section" aria-labelledby="overview-governance-heading">
    <header class="overview-section-header">
      <h2 id="overview-governance-heading">{{ overviewGovernanceHeading }}</h2>
      <p class="overview-kicker">{{ overviewGovernanceLead }}</p>
    </header>

    <dl class="overview-governance-roles">
      <div>
        <dt>{{ overviewGovernanceAiTitle }}</dt>
        <dd>{{ overviewGovernanceAiCopy }}</dd>
      </div>
      <div>
        <dt>{{ overviewGovernanceHumanTitle }}</dt>
        <dd>{{ overviewGovernanceHumanCopy }}</dd>
      </div>
    </dl>

    <h3 class="overview-subsection-heading">Human decisions</h3>
    <dl class="overview-governance-decisions">
      <div v-for="decision in overviewGovernanceDecisions" :key="decision.id">
        <dt>{{ decision.name }}</dt>
        <dd>{{ decision.consequence }}</dd>
      </div>
    </dl>
  </section>
</template>
