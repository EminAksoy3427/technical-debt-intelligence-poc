<script setup lang="ts">
import type { GroundedClaimItem, StructuredAssessmentPresentation } from '~/types/agentRun'

const props = defineProps<{
  assessment: StructuredAssessmentPresentation
}>()

function claimKey(claim: GroundedClaimItem, index: number): string {
  return `${claim.statement}:${index}`
}

const recommendationItems = computed(() => {
  if (props.assessment.recommendation == null) {
    return []
  }

  return props.assessment.recommendation
    .split(/\n+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0)
})
</script>

<template>
  <section
    class="candidate-investigation-assessment"
    aria-labelledby="candidate-structured-assessment-heading"
  >
    <div class="candidate-investigation-header-row">
      <h3 id="candidate-structured-assessment-heading">Assessment</h3>
      <span class="badge badge--neutral">{{ assessment.outcomeLabel }}</span>
    </div>

    <p v-if="assessment.conclusion" class="candidate-assessment-summary">
      {{ assessment.conclusion.statement }}
    </p>
    <CandidateGroundingReferences
      v-if="assessment.conclusion"
      :references="assessment.conclusion.references"
    />
    <p v-else class="candidate-empty-value">No supported conclusion was returned.</p>

    <section
      v-if="assessment.supportingClaims.length > 0"
      class="candidate-investigation-subsection"
      aria-labelledby="candidate-assessment-claims-heading"
    >
      <h4 id="candidate-assessment-claims-heading">Supporting findings</h4>
      <ul class="candidate-record-list">
        <li
          v-for="(claim, index) in assessment.supportingClaims"
          :key="claimKey(claim, index)"
          class="candidate-finding"
        >
          <p class="candidate-record-kicker">Finding</p>
          <p class="candidate-finding-statement">{{ claim.statement }}</p>
          <CandidateGroundingReferences :references="claim.references" />
        </li>
      </ul>
    </section>

    <section
      class="candidate-investigation-subsection"
      aria-labelledby="candidate-assessment-gaps-heading"
    >
      <h4 id="candidate-assessment-gaps-heading">Evidence gaps</h4>
      <div class="candidate-evidence-gaps">
        <section aria-labelledby="candidate-assessment-missing-heading">
          <h5 id="candidate-assessment-missing-heading" class="candidate-gaps-heading">
            Missing evidence
          </h5>
          <ul
            v-if="assessment.missingEvidence.length > 0"
            class="candidate-investigation-note-list"
          >
            <li v-for="item in assessment.missingEvidence" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="candidate-empty-value">None recorded.</p>
        </section>
        <section aria-labelledby="candidate-assessment-uncertainties-heading">
          <h5 id="candidate-assessment-uncertainties-heading" class="candidate-gaps-heading">
            Uncertainties
          </h5>
          <ul
            v-if="assessment.uncertainties.length > 0"
            class="candidate-investigation-note-list"
          >
            <li v-for="item in assessment.uncertainties" :key="item">{{ item }}</li>
          </ul>
          <p v-else class="candidate-empty-value">None recorded.</p>
        </section>
      </div>
    </section>

    <section
      class="candidate-investigation-subsection"
      aria-labelledby="candidate-assessment-recommendation-heading"
    >
      <h4 id="candidate-assessment-recommendation-heading">Recommended next steps</h4>
      <p v-if="recommendationItems.length > 0" class="candidate-section-note">
        Proposed next direction, not an approved action.
      </p>
      <ol
        v-if="recommendationItems.length > 1"
        class="candidate-recommendation-list"
      >
        <li v-for="item in recommendationItems" :key="item">{{ item }}</li>
      </ol>
      <p v-else-if="recommendationItems.length === 1" class="candidate-recommendation-text">
        {{ recommendationItems[0] }}
      </p>
      <p v-else class="candidate-empty-value">None recorded.</p>
    </section>
  </section>
</template>
