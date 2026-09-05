from app.agent.audit_contracts import (
    AgentRunStopReason,
    AssessmentOutcome,
    EvidenceReference,
    GroundedClaim,
    StructuredAssessment,
    ToolExecutionReference,
)
from app.agent.candidate_tools import ReadCandidateEvidenceResult
from app.agent.runtime_contracts import (
    FinalAssessmentDecision,
    InvestigationRuntimeContext,
    ProviderStep,
    ToolCallRequest,
    ToolResultObservation,
)

_INVESTIGATION_TOOL_ORDER = (
    "read_candidate_evidence",
    "read_candidate_dependency_context",
    "read_candidate_enterprise_context",
)


class DeterministicCandidateInvestigationProvider:
    """Server-owned PoC strategy that uses persisted facts without an LLM."""

    def next_step(self, context: InvestigationRuntimeContext) -> ProviderStep:
        completed_tool_count = len(context.tool_results)
        if completed_tool_count < len(_INVESTIGATION_TOOL_ORDER):
            return ToolCallRequest(
                tool_id=_INVESTIGATION_TOOL_ORDER[completed_tool_count],
                arguments={"candidate_id": str(context.candidate_id)},
            )

        observations = context.tool_results
        self._require_expected_observations(observations)
        evidence_result = ReadCandidateEvidenceResult.model_validate(
            observations[0].result
        )
        if not evidence_result.evidence:
            return FinalAssessmentDecision(
                assessment=StructuredAssessment(
                    outcome=AssessmentOutcome.ABSTAINED,
                    missing_evidence=(
                        "No persisted Evidence was available for the Candidate.",
                    ),
                    uncertainties=(
                        "No live model inference was performed by this deterministic "
                        "investigation.",
                    ),
                    stop_reason=AgentRunStopReason.MISSING_EVIDENCE,
                )
            )

        evidence_references = tuple(
            EvidenceReference(evidence_id=evidence.evidence_id)
            for evidence in evidence_result.evidence
        )
        dependency_observation = observations[1]
        enterprise_observation = observations[2]
        return FinalAssessmentDecision(
            assessment=StructuredAssessment(
                outcome=AssessmentOutcome.SUPPORTED,
                conclusion=GroundedClaim(
                    statement=(
                        "Persisted Evidence is available for human review of the "
                        "Candidate hypothesis."
                    ),
                    references=evidence_references,
                ),
                supporting_claims=(
                    GroundedClaim(
                        statement=(
                            "Persisted dependency reachability context was retrieved; "
                            "reachability does not establish causality or risk."
                        ),
                        references=(
                            ToolExecutionReference(
                                tool_execution_id=(
                                    dependency_observation.tool_execution_id
                                )
                            ),
                        ),
                    ),
                    GroundedClaim(
                        statement=(
                            "Persisted enterprise context was retrieved; criticality "
                            "does not establish risk."
                        ),
                        references=(
                            ToolExecutionReference(
                                tool_execution_id=enterprise_observation.tool_execution_id
                            ),
                        ),
                    ),
                ),
                uncertainties=(
                    "This deterministic investigation does not use a live model.",
                ),
                recommendation=(
                    "An authorized human must decide any Candidate lifecycle action."
                ),
            )
        )

    @staticmethod
    def _require_expected_observations(
        observations: tuple[ToolResultObservation, ...],
    ) -> None:
        observed_tool_ids = tuple(item.tool_id for item in observations)
        if observed_tool_ids != _INVESTIGATION_TOOL_ORDER:
            raise ValueError("Deterministic investigation received an invalid trace")

