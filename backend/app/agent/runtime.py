import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from app.agent.audit_contracts import (
    AgentRun,
    AgentRunStatus,
    AgentRunStopReason,
    AssessmentOutcome,
    EvidenceReference,
    PolicyDecisionRecord,
    StructuredAssessment,
    ToolExecution,
    ToolExecutionReference,
    ToolExecutionStatus,
    build_candidate_tool_input_trace,
)
from app.agent.candidate_tools import ReadCandidateEvidenceResult
from app.agent.contracts import CandidateToolInput, ToolRegistration
from app.agent.policy import (
    PolicyDecision,
    ToolAuthorizationContext,
    evaluate_candidate_tool_policy,
)
from app.agent.registry import ToolRegistry
from app.agent.runtime_contracts import (
    AgentRuntimeLimits,
    FinalAssessmentDecision,
    InvestigationProvider,
    InvestigationRuntimeContext,
    ProviderStep,
    RuntimeToolDescriptor,
    ToolCallRequest,
    ToolResultObservation,
)
from app.core.config import Settings, settings
from app.infrastructure.database.agent_audit_persistence import (
    AgentRunAuditAggregate,
    append_policy_decision,
    append_tool_execution,
    create_agent_run,
    load_agent_run_audit,
    update_agent_run,
)

_PROVIDER_STEP_ADAPTER = TypeAdapter(ProviderStep)


class RuntimeClock(Protocol):
    def now(self) -> datetime: ...

    def monotonic(self) -> float: ...


class SystemRuntimeClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

    def monotonic(self) -> float:
        return time.monotonic()


def runtime_limits_from_settings(
    app_settings: Settings = settings,
) -> AgentRuntimeLimits:
    return AgentRuntimeLimits(
        max_iterations=app_settings.agent_max_iterations,
        max_tool_calls=app_settings.agent_max_tool_calls,
        run_timeout_seconds=app_settings.agent_run_timeout_seconds,
        tool_timeout_seconds=app_settings.agent_tool_timeout_seconds,
    )


def run_candidate_investigation(
    session: Session,
    *,
    candidate_id: UUID,
    provider: InvestigationProvider,
    registry: ToolRegistry,
    authorization: ToolAuthorizationContext,
    limits: AgentRuntimeLimits | None = None,
    clock: RuntimeClock | None = None,
    new_uuid: Callable[[], UUID] = uuid4,
) -> AgentRunAuditAggregate:
    """Run one bounded investigation and commit durable audit checkpoints."""
    runtime_limits = limits or runtime_limits_from_settings()
    runtime_clock = clock or SystemRuntimeClock()
    run_id = authorization.investigation_id
    created_at = runtime_clock.now()
    started_at = created_at
    deadline = runtime_clock.monotonic() + runtime_limits.run_timeout_seconds

    create_agent_run(
        session,
        AgentRun(
            agent_run_id=run_id,
            candidate_id=candidate_id,
            status=AgentRunStatus.CREATED,
            created_at=created_at,
        ),
    )
    session.commit()
    update_agent_run(
        session,
        AgentRun(
            agent_run_id=run_id,
            candidate_id=candidate_id,
            status=AgentRunStatus.RUNNING,
            created_at=created_at,
            started_at=started_at,
        ),
    )
    session.commit()

    observations: list[ToolResultObservation] = []
    tool_call_count = 0
    sequence_number = 0
    descriptors = _runtime_descriptors(registry)

    for iteration_index in range(runtime_limits.max_iterations):
        if runtime_clock.monotonic() >= deadline:
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.BUDGET_EXHAUSTED,
                detail="The overall investigation time budget was exhausted.",
            )

        context = InvestigationRuntimeContext(
            candidate_id=candidate_id,
            available_tools=descriptors,
            tool_results=tuple(observations),
            remaining_iterations=runtime_limits.max_iterations - iteration_index,
            remaining_tool_calls=runtime_limits.max_tool_calls - tool_call_count,
        )
        try:
            raw_step = provider.next_step(context)
            step = _PROVIDER_STEP_ADAPTER.validate_python(raw_step)
        except Exception:
            return _finish_failed(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.PROVIDER_FAILURE,
            )

        if runtime_clock.monotonic() >= deadline:
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.BUDGET_EXHAUSTED,
                detail="The overall investigation time budget was exhausted.",
            )

        if isinstance(step, FinalAssessmentDecision):
            return _complete_from_provider_assessment(
                session,
                step=step,
                observations=tuple(observations),
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
            )

        sequence_number += 1
        requested_at = runtime_clock.now()
        request_tick = runtime_clock.monotonic()
        try:
            registration = registry.get(step.tool_id)
        except KeyError:
            unavailable = _failed_tool_execution(
                execution_id=new_uuid(),
                run_id=run_id,
                candidate_id=candidate_id,
                step=step,
                tool_version="unresolved",
                sequence_number=sequence_number,
                status=ToolExecutionStatus.UNAVAILABLE,
                requested_at=requested_at,
                finished_at=runtime_clock.now(),
                duration_ms=_duration_ms(request_tick, runtime_clock.monotonic()),
                error_code="TOOL_UNAVAILABLE",
                error_message="Requested tool is unavailable.",
            )
            append_tool_execution(session, unavailable)
            session.commit()
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.TOOL_UNAVAILABLE,
                detail="The requested tool was unavailable.",
            )

        try:
            validated_input = registration.input_model.model_validate(step.arguments)
            if not isinstance(validated_input, CandidateToolInput):
                raise ValueError("Runtime tools must use CandidateToolInput")
        except (ValidationError, ValueError):
            invalid = _failed_tool_execution(
                execution_id=new_uuid(),
                run_id=run_id,
                candidate_id=candidate_id,
                step=step,
                tool_version=registration.descriptor.version,
                sequence_number=sequence_number,
                status=ToolExecutionStatus.INVALID_ARGUMENTS,
                requested_at=requested_at,
                finished_at=runtime_clock.now(),
                duration_ms=_duration_ms(request_tick, runtime_clock.monotonic()),
                error_code="INVALID_TOOL_ARGUMENTS",
                error_message="Tool arguments did not match the registered schema.",
            )
            append_tool_execution(session, invalid)
            session.commit()
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.INVALID_TOOL_ARGUMENTS,
                detail="The requested tool arguments were invalid.",
            )

        if tool_call_count >= runtime_limits.max_tool_calls:
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.BUDGET_EXHAUSTED,
                detail="The tool-call budget was exhausted.",
            )

        tool_call_count += 1
        policy = evaluate_candidate_tool_policy(
            registration,
            validated_input.candidate_id,
            authorization,
        )
        execution_id = new_uuid()
        policy_record = PolicyDecisionRecord(
            tool_execution_id=execution_id,
            decision=policy.decision,
            requested_effect=registration.descriptor.effect,
            requested_risk=registration.descriptor.risk,
            required_scopes=registration.descriptor.required_scopes,
            granted_scopes=authorization.granted_scopes,
            maximum_risk=authorization.maximum_risk,
            rule_id=policy.rule_id,
            reason_code=policy.reason_code,
            decided_at=runtime_clock.now(),
        )

        if policy.decision is PolicyDecision.DENY:
            trace = build_candidate_tool_input_trace(validated_input)
            denied = ToolExecution(
                tool_execution_id=execution_id,
                agent_run_id=run_id,
                sequence_number=sequence_number,
                tool_id=registration.descriptor.tool_id,
                tool_version=registration.descriptor.version,
                input_hash=trace.input_hash,
                safe_input_summary=trace.safe_input_summary,
                status=ToolExecutionStatus.DENIED,
                requested_at=requested_at,
                finished_at=runtime_clock.now(),
                duration_ms=_duration_ms(request_tick, runtime_clock.monotonic()),
                error_code=policy.reason_code,
                error_message="Tool request was denied by policy.",
            )
            _persist_tool_and_policy(session, denied, policy_record)
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.POLICY_DENIED,
                detail="Policy denied the requested tool.",
            )

        started_tool_at = runtime_clock.now()
        started_tool_tick = runtime_clock.monotonic()
        try:
            result = registration.executor(validated_input)
            validated_result = registration.result_model.model_validate(result)
        except Exception:
            failed = _executed_tool_failure(
                execution_id=execution_id,
                run_id=run_id,
                registration=registration,
                validated_input=validated_input,
                sequence_number=sequence_number,
                requested_at=requested_at,
                started_at=started_tool_at,
                finished_at=runtime_clock.now(),
                duration_ms=_duration_ms(
                    started_tool_tick,
                    runtime_clock.monotonic(),
                ),
                status=ToolExecutionStatus.FAILED,
                error_code="TOOL_EXECUTION_FAILED",
                error_message="Tool execution failed.",
            )
            _persist_tool_and_policy(session, failed, policy_record)
            return _finish_failed(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=AgentRunStopReason.INTERNAL_FAILURE,
            )

        finished_tool_tick = runtime_clock.monotonic()
        finished_tool_at = runtime_clock.now()
        duration_ms = _duration_ms(started_tool_tick, finished_tool_tick)
        if (
            finished_tool_tick - started_tool_tick
            >= runtime_limits.tool_timeout_seconds
            or finished_tool_tick >= deadline
        ):
            timed_out = _executed_tool_failure(
                execution_id=execution_id,
                run_id=run_id,
                registration=registration,
                validated_input=validated_input,
                sequence_number=sequence_number,
                requested_at=requested_at,
                started_at=started_tool_at,
                finished_at=finished_tool_at,
                duration_ms=duration_ms,
                status=ToolExecutionStatus.TIMED_OUT,
                error_code="TOOL_TIMEOUT",
                error_message="Tool execution exceeded a runtime deadline.",
            )
            _persist_tool_and_policy(session, timed_out, policy_record)
            stop_reason = (
                AgentRunStopReason.TOOL_TIMEOUT
                if finished_tool_tick - started_tool_tick
                >= runtime_limits.tool_timeout_seconds
                else AgentRunStopReason.BUDGET_EXHAUSTED
            )
            return _finish_abstained(
                session,
                run_id=run_id,
                candidate_id=candidate_id,
                created_at=created_at,
                started_at=started_at,
                clock=runtime_clock,
                stop_reason=stop_reason,
                detail="A runtime deadline was exceeded.",
            )

        evidence_references = _evidence_references(validated_result)
        trace = build_candidate_tool_input_trace(validated_input)
        succeeded = ToolExecution(
            tool_execution_id=execution_id,
            agent_run_id=run_id,
            sequence_number=sequence_number,
            tool_id=registration.descriptor.tool_id,
            tool_version=registration.descriptor.version,
            input_hash=trace.input_hash,
            safe_input_summary=trace.safe_input_summary,
            status=ToolExecutionStatus.SUCCEEDED,
            requested_at=requested_at,
            started_at=started_tool_at,
            finished_at=finished_tool_at,
            duration_ms=duration_ms,
            result_references=evidence_references,
        )
        _persist_tool_and_policy(session, succeeded, policy_record)
        observations.append(
            ToolResultObservation(
                tool_execution_id=execution_id,
                sequence_number=sequence_number,
                tool_id=registration.descriptor.tool_id,
                tool_version=registration.descriptor.version,
                status=ToolExecutionStatus.SUCCEEDED,
                result=validated_result.model_dump(mode="json"),
                references=(
                    *evidence_references,
                    ToolExecutionReference(tool_execution_id=execution_id),
                ),
            )
        )

    return _finish_abstained(
        session,
        run_id=run_id,
        candidate_id=candidate_id,
        created_at=created_at,
        started_at=started_at,
        clock=runtime_clock,
        stop_reason=AgentRunStopReason.BUDGET_EXHAUSTED,
        detail="The provider-step iteration budget was exhausted.",
    )


def _runtime_descriptors(registry: ToolRegistry) -> tuple[RuntimeToolDescriptor, ...]:
    return tuple(
        RuntimeToolDescriptor(
            tool_id=registration.descriptor.tool_id,
            version=registration.descriptor.version,
            description=registration.descriptor.description,
            effect=registration.descriptor.effect,
            risk=registration.descriptor.risk,
            required_scopes=tuple(sorted(registration.descriptor.required_scopes)),
            input_schema=registration.input_model.model_json_schema(),
        )
        for registration in registry.list()
    )


def _failed_tool_execution(
    *,
    execution_id: UUID,
    run_id: UUID,
    candidate_id: UUID,
    step: ToolCallRequest,
    tool_version: str,
    sequence_number: int,
    status: ToolExecutionStatus,
    requested_at: datetime,
    finished_at: datetime,
    duration_ms: int,
    error_code: str,
    error_message: str,
) -> ToolExecution:
    trace = build_candidate_tool_input_trace(
        CandidateToolInput(candidate_id=candidate_id)
    )
    return ToolExecution(
        tool_execution_id=execution_id,
        agent_run_id=run_id,
        sequence_number=sequence_number,
        tool_id=step.tool_id,
        tool_version=tool_version,
        input_hash=trace.input_hash,
        safe_input_summary=trace.safe_input_summary,
        status=status,
        requested_at=requested_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        error_code=error_code,
        error_message=error_message,
    )


def _executed_tool_failure(
    *,
    execution_id: UUID,
    run_id: UUID,
    registration: ToolRegistration[BaseModel, BaseModel],
    validated_input: CandidateToolInput,
    sequence_number: int,
    requested_at: datetime,
    started_at: datetime,
    finished_at: datetime,
    duration_ms: int,
    status: ToolExecutionStatus,
    error_code: str,
    error_message: str,
) -> ToolExecution:
    trace = build_candidate_tool_input_trace(validated_input)
    return ToolExecution(
        tool_execution_id=execution_id,
        agent_run_id=run_id,
        sequence_number=sequence_number,
        tool_id=registration.descriptor.tool_id,
        tool_version=registration.descriptor.version,
        input_hash=trace.input_hash,
        safe_input_summary=trace.safe_input_summary,
        status=status,
        requested_at=requested_at,
        started_at=started_at,
        finished_at=finished_at,
        duration_ms=duration_ms,
        error_code=error_code,
        error_message=error_message,
    )


def _persist_tool_and_policy(
    session: Session,
    execution: ToolExecution,
    policy: PolicyDecisionRecord,
) -> None:
    append_tool_execution(session, execution)
    append_policy_decision(session, policy)
    session.commit()


def _evidence_references(
    result: BaseModel,
) -> tuple[EvidenceReference, ...]:
    if not isinstance(result, ReadCandidateEvidenceResult):
        return ()
    return tuple(
        EvidenceReference(evidence_id=evidence.evidence_id)
        for evidence in result.evidence
    )


def _complete_from_provider_assessment(
    session: Session,
    *,
    step: FinalAssessmentDecision,
    observations: tuple[ToolResultObservation, ...],
    run_id: UUID,
    candidate_id: UUID,
    created_at: datetime,
    started_at: datetime,
    clock: RuntimeClock,
) -> AgentRunAuditAggregate:
    try:
        assessment = StructuredAssessment.model_validate(step.assessment)
        _validate_assessment_references(assessment, observations)
    except (ValidationError, ValueError):
        return _finish_failed(
            session,
            run_id=run_id,
            candidate_id=candidate_id,
            created_at=created_at,
            started_at=started_at,
            clock=clock,
            stop_reason=AgentRunStopReason.PROVIDER_FAILURE,
        )

    if assessment.outcome is AssessmentOutcome.SUPPORTED:
        completed = AgentRun(
            agent_run_id=run_id,
            candidate_id=candidate_id,
            status=AgentRunStatus.COMPLETED,
            created_at=created_at,
            started_at=started_at,
            completed_at=clock.now(),
            structured_assessment=assessment,
        )
        update_agent_run(session, completed)
        session.commit()
        return _load_required_aggregate(session, run_id)

    stop_reason = assessment.stop_reason
    if stop_reason is None:
        stop_reason = (
            AgentRunStopReason.MISSING_EVIDENCE
            if assessment.missing_evidence
            else AgentRunStopReason.CONFLICTING_EVIDENCE
        )
    abstained = AgentRun(
        agent_run_id=run_id,
        candidate_id=candidate_id,
        status=AgentRunStatus.ABSTAINED,
        created_at=created_at,
        started_at=started_at,
        completed_at=clock.now(),
        structured_assessment=assessment,
        stop_reason=stop_reason,
    )
    update_agent_run(session, abstained)
    session.commit()
    return _load_required_aggregate(session, run_id)


def _validate_assessment_references(
    assessment: StructuredAssessment,
    observations: tuple[ToolResultObservation, ...],
) -> None:
    available_references = {
        (reference.reference_type.value, _reference_id(reference))
        for observation in observations
        for reference in observation.references
    }
    claims = (
        *((assessment.conclusion,) if assessment.conclusion is not None else ()),
        *assessment.supporting_claims,
    )
    for claim in claims:
        for reference in claim.references:
            identity = (reference.reference_type.value, _reference_id(reference))
            if identity not in available_references:
                raise ValueError("Assessment contains an unavailable reference")


def _reference_id(reference: EvidenceReference | ToolExecutionReference) -> UUID:
    if isinstance(reference, EvidenceReference):
        return reference.evidence_id
    return reference.tool_execution_id


def _finish_abstained(
    session: Session,
    *,
    run_id: UUID,
    candidate_id: UUID,
    created_at: datetime,
    started_at: datetime,
    clock: RuntimeClock,
    stop_reason: AgentRunStopReason,
    detail: str,
) -> AgentRunAuditAggregate:
    assessment = StructuredAssessment(
        outcome=AssessmentOutcome.ABSTAINED,
        uncertainties=(detail,),
        stop_reason=stop_reason,
    )
    agent_run = AgentRun(
        agent_run_id=run_id,
        candidate_id=candidate_id,
        status=AgentRunStatus.ABSTAINED,
        created_at=created_at,
        started_at=started_at,
        completed_at=clock.now(),
        structured_assessment=assessment,
        stop_reason=stop_reason,
    )
    update_agent_run(session, agent_run)
    session.commit()
    return _load_required_aggregate(session, run_id)


def _finish_failed(
    session: Session,
    *,
    run_id: UUID,
    candidate_id: UUID,
    created_at: datetime,
    started_at: datetime,
    clock: RuntimeClock,
    stop_reason: AgentRunStopReason,
) -> AgentRunAuditAggregate:
    agent_run = AgentRun(
        agent_run_id=run_id,
        candidate_id=candidate_id,
        status=AgentRunStatus.FAILED,
        created_at=created_at,
        started_at=started_at,
        completed_at=clock.now(),
        stop_reason=stop_reason,
    )
    update_agent_run(session, agent_run)
    session.commit()
    return _load_required_aggregate(session, run_id)


def _load_required_aggregate(
    session: Session,
    run_id: UUID,
) -> AgentRunAuditAggregate:
    aggregate = load_agent_run_audit(session, run_id)
    if aggregate is None:
        raise RuntimeError("Persisted AgentRun audit aggregate is unavailable")
    return aggregate


def _duration_ms(started: float, finished: float) -> int:
    return max(0, int((finished - started) * 1000))
