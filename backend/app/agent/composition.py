from typing import cast

from pydantic import BaseModel

from app.agent.candidate_tools import create_read_candidate_evidence_registration
from app.agent.contracts import ToolRegistration
from app.agent.ports import CandidateInvestigationReader
from app.agent.registry import ToolRegistry


def build_candidate_tool_registry(
    reader: CandidateInvestigationReader,
) -> ToolRegistry:
    """Compose the explicit production Candidate Tool registry."""
    registration = create_read_candidate_evidence_registration(reader)
    return ToolRegistry(
        registrations=(
            cast(ToolRegistration[BaseModel, BaseModel], registration),
        )
    )
