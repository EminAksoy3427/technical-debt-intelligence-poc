<script setup lang="ts">
import type { GroundedClaimItem, StructuredAssessmentPresentation } from '~/types/agentRun'

defineProps<{
  assessment: StructuredAssessmentPresentation
}>()

function claimKey(claim: GroundedClaimItem, index: number): string {
  return `${claim.statement}:${index}`
}
</script>

<template>
  <section
    class="candidate-detail-section"
    aria-labelledby="candidate-structured-assessment-heading"
  >
    <h3 id="candidate-structured-assessment-heading">Structured assessment</h3>
    <p class="candidate-section-introduction">
      This assessment interprets existing evidence and context. It does not validate
      the Candidate or authorize a lifecycle action.
    </p>

    <dl class="candidate-detail-list candidate-detail-list--scan">
      <div>
        <dt>Outcome</dt>
        <dd>
          <span class="badge badge--neutral">{{ assessment.outcomeLabel }}</span>
        </dd>
      </div>
      <div v-if="assessment.stopReasonLabel != null">
        <dt>Stop reason</dt>
        <dd>{{ assessment.stopReasonLabel }}</dd>
      </div>
    </dl>

    <section
      v-if="assessment.conclusion"
      class="candidate-detail-subsection"
      aria-labelledby="candidate-assessment-conclusion-heading"
    >
      <h4 id="candidate-assessment-conclusion-heading">Conclusion</h4>
      <p class="candidate-correlation-rationale">{{ assessment.conclusion.statement }}</p>
      <CandidateGroundingReferences :references="assessment.conclusion.references" />
    </section>

    <section
      v-if="assessment.supportingClaims.length > 0"
      class="candidate-detail-subsection"
      aria-labelledby="candidate-assessment-claims-heading"
    >
      <h4 id="candidate-assessment-claims-heading">Supporting claims</h4>
      <ul class="candidate-membership-list candidate-membership-list--cards">
        <li v-for="(claim, index) in assessment.supportingClaims" :key="claimKey(claim, index)">
          <p class="candidate-fact-primary">{{ claim.statement }}</p>
          <CandidateGroundingReferences :references="claim.references" />
        </li>
      </ul>
    </section>

    <section
      v-if="assessment.missingEvidence.length > 0"
      class="candidate-detail-subsection"
      aria-labelledby="candidate-assessment-missing-heading"
    >
      <h4 id="candidate-assessment-missing-heading">Missing evidence</h4>
      <ul class="candidate-investigation-note-list">
        <li v-for="item in assessment.missingEvidence" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section
      v-if="assessment.uncertainties.length > 0"
      class="candidate-detail-subsection"
      aria-labelledby="candidate-assessment-uncertainties-heading"
    >
      <h4 id="candidate-assessment-uncertainties-heading">Uncertainties</h4>
      <ul class="candidate-investigation-note-list">
        <li v-for="item in assessment.uncertainties" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section
      v-if="assessment.recommendation != null"
      class="candidate-detail-subsection"
      aria-labelledby="candidate-assessment-recommendation-heading"
    >
      <h4 id="candidate-assessment-recommendation-heading">Proposed next direction</h4>
      <p class="candidate-section-introduction">
        This is a proposed next direction, not an approved action.
      </p>
      <p class="candidate-correlation-rationale">{{ assessment.recommendation }}</p>
    </section>
  </section>
</template>
