from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.agent.audit_contracts import (
    AgentRun,
    AgentRunStatus,
    AgentRunStopReason,
    AssessmentOutcome,
    CandidateToolInputSummary,
    EvidenceReference,
    GroundedClaim,
    PolicyDecisionRecord,
    StructuredAssessment,
    ToolExecution,
    ToolExecutionReference,
    ToolExecutionStatus,
    build_candidate_tool_input_trace,
)
from app.agent.contracts import CandidateToolInput, ToolEffect, ToolRisk
from app.agent.policy import PolicyDecision

CREATED_AT = datetime(2026, 9, 5, 9, 0, tzinfo=UTC)
STARTED_AT = CREATED_AT + timedelta(seconds=1)
COMPLETED_AT = STARTED_AT + timedelta(seconds=1)


def _grounded_claim() -> GroundedClaim:
    return GroundedClaim(
        statement="The Candidate has persisted supporting Evidence.",
        references=(
            EvidenceReference(
                evidence_id=UUID("00000000-0000-0000-0000-000000000601")
            ),
            ToolExecutionReference(
                tool_execution_id=UUID(
                    "00000000-0000-0000-0000-000000000801"
                )
            ),
        ),
    )


def _supported_assessment() -> StructuredAssessment:
    return StructuredAssessment(
        outcome=AssessmentOutcome.SUPPORTED,
        conclusion=_grounded_claim(),
        recommendation="Ask a human reviewer to inspect the grounded claim.",
    )


def test_grounded_claim_requires_nonempty_typed_references() -> None:
    with pytest.raises(ValidationError, match="at least 1 item"):
        GroundedClaim(statement="A material fact.", references=())

    claim = _grounded_claim()
    assert isinstance(claim.references[0], EvidenceReference)
    assert isinstance(claim.references[1], ToolExecutionReference)


def test_supported_assessment_requires_a_grounded_conclusion() -> None:
    with pytest.raises(ValidationError, match="grounded conclusion"):
        StructuredAssessment(outcome=AssessmentOutcome.SUPPORTED)

    assessment = _supported_assessment()
    assert assessment.conclusion == _grounded_claim()


def test_abstained_assessment_cannot_masquerade_as_supported() -> None:
    with pytest.raises(ValidationError, match="must not contain a conclusion"):
        StructuredAssessment(
            outcome=AssessmentOutcome.ABSTAINED,
            conclusion=_grounded_claim(),
            stop_reason=AgentRunStopReason.MISSING_EVIDENCE,
        )

    with pytest.raises(ValidationError, match="meaningful reason"):
        StructuredAssessment(outcome=AssessmentOutcome.ABSTAINED)

    assessment = StructuredAssessment(
        outcome=AssessmentOutcome.ABSTAINED,
        missing_evidence=("A current dependency inventory is missing.",),
        stop_reason=AgentRunStopReason.MISSING_EVIDENCE,
    )
    assert assessment.conclusion is None


def test_agent_run_terminal_state_semantics_are_enforced() -> None:
    with pytest.raises(ValidationError, match="requires a stop reason"):
        AgentRun(
            agent_run_id=uuid4(),
            candidate_id=uuid4(),
            status=AgentRunStatus.ABSTAINED,
            created_at=CREATED_AT,
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
        )

    with pytest.raises(ValidationError, match="supported Structured Assessment"):
        AgentRun(
            agent_run_id=uuid4(),
            candidate_id=uuid4(),
            status=AgentRunStatus.COMPLETED,
            created_at=CREATED_AT,
            started_at=STARTED_AT,
            completed_at=COMPLETED_AT,
        )

    completed = AgentRun(
        agent_run_id=uuid4(),
        candidate_id=uuid4(),
        status=AgentRunStatus.COMPLETED,
        created_at=CREATED_AT,
        started_at=STARTED_AT,
        completed_at=COMPLETED_AT,
        structured_assessment=_supported_assessment(),
    )
    assert completed.stop_reason is None


def test_candidate_input_trace_is_allowlisted_and_deterministic() -> None:
    candidate_id = UUID("00000000-0000-0000-0000-000000000701")
    first = build_candidate_tool_input_trace(
        CandidateToolInput(candidate_id=candidate_id)
    )
    second = build_candidate_tool_input_trace(
        CandidateToolInput(candidate_id=candidate_id)
    )

    assert first == second
    assert len(first.input_hash) == 64
    assert first.safe_input_summary.model_dump(mode="json") == {
        "candidate_id": str(candidate_id)
    }


def test_tool_execution_rejects_negative_duration_and_unsafe_result_shapes() -> None:
    trace = build_candidate_tool_input_trace(
        CandidateToolInput(candidate_id=uuid4())
    )
    values = {
        "tool_execution_id": uuid4(),
        "agent_run_id": uuid4(),
        "sequence_number": 1,
        "tool_id": "read_candidate_evidence",
        "tool_version": "1.0",
        "input_hash": trace.input_hash,
        "safe_input_summary": trace.safe_input_summary,
        "status": ToolExecutionStatus.SUCCEEDED,
        "requested_at": CREATED_AT,
        "started_at": STARTED_AT,
        "finished_at": COMPLETED_AT,
        "duration_ms": -1,
    }
    with pytest.raises(ValidationError, match="greater than or equal to 0"):
        ToolExecution.model_validate(values)

    values["duration_ms"] = 50
    values["raw_input"] = {"token": "must-not-be-accepted"}
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ToolExecution.model_validate(values)


def test_unsuccessful_tool_execution_requires_a_safe_error_code() -> None:
    summary = CandidateToolInputSummary(candidate_id=uuid4())
    with pytest.raises(ValidationError, match="safe error code"):
        ToolExecution(
            tool_execution_id=uuid4(),
            agent_run_id=uuid4(),
            sequence_number=1,
            tool_id="read_candidate_evidence",
            tool_version="1.0",
            input_hash="0" * 64,
            safe_input_summary=summary,
            status=ToolExecutionStatus.DENIED,
            requested_at=CREATED_AT,
            finished_at=COMPLETED_AT,
            duration_ms=1,
        )


def test_policy_decision_record_is_typed_and_rejects_untrusted_extra_facts() -> None:
    values = {
        "tool_execution_id": uuid4(),
        "decision": PolicyDecision.ALLOW,
        "requested_effect": ToolEffect.READ,
        "requested_risk": ToolRisk.LOW,
        "required_scopes": frozenset({"candidate:read"}),
        "granted_scopes": frozenset({"candidate:read"}),
        "maximum_risk": ToolRisk.LOW,
        "rule_id": "allow",
        "reason_code": "POLICY_ALLOWED",
        "decided_at": CREATED_AT,
    }
    decision = PolicyDecisionRecord.model_validate(values)
    assert decision.requested_effect is ToolEffect.READ

    values["model_supplied_policy"] = True
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        PolicyDecisionRecord.model_validate(values)


def test_audit_contracts_expose_no_hidden_reasoning_fields() -> None:
    prohibited = {
        "chain_of_thought",
        "reasoning",
        "scratchpad",
        "internal_reasoning",
        "thoughts",
        "raw_prompt",
        "raw_model_response",
    }
    contract_types = (
        StructuredAssessment,
        AgentRun,
        ToolExecution,
        PolicyDecisionRecord,
    )

    for contract_type in contract_types:
        assert prohibited.isdisjoint(contract_type.model_fields)
