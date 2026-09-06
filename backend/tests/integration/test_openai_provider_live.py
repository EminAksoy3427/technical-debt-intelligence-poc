import os
from uuid import uuid4

import pytest

from app.agent.contracts import CandidateToolInput, ToolEffect, ToolRisk
from app.agent.provider_composition import build_candidate_investigation_provider
from app.agent.runtime_contracts import (
    FinalAssessmentDecision,
    InvestigationRuntimeContext,
    RuntimeToolDescriptor,
    ToolCallRequest,
)
from app.core.config import AgentProviderName, Settings


@pytest.mark.external
def test_explicit_live_openai_provider_smoke() -> None:
    if os.getenv("RUN_OPENAI_LIVE_TEST") != "1":
        pytest.skip("Set RUN_OPENAI_LIVE_TEST=1 to permit a paid live request")

    app_settings = Settings()
    if app_settings.agent_provider is not AgentProviderName.OPENAI:
        pytest.skip("Set AGENT_PROVIDER=openai for the live provider smoke test")

    provider = build_candidate_investigation_provider(app_settings)
    step = provider.next_step(
        InvestigationRuntimeContext(
            candidate_id=uuid4(),
            available_tools=(
                RuntimeToolDescriptor(
                    tool_id="read_candidate_evidence",
                    version="1.0.0",
                    description="Read grounded Evidence for one Candidate.",
                    effect=ToolEffect.READ,
                    risk=ToolRisk.LOW,
                    required_scopes=("candidate:read",),
                    input_schema=CandidateToolInput.model_json_schema(),
                ),
            ),
            tool_results=(),
            remaining_iterations=2,
            remaining_tool_calls=1,
        )
    )

    assert isinstance(step, ToolCallRequest | FinalAssessmentDecision)
