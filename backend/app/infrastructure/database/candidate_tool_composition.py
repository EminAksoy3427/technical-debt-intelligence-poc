from sqlalchemy.orm import Session

from app.agent.composition import build_candidate_tool_registry
from app.agent.registry import ToolRegistry
from app.infrastructure.database.candidate_investigation_reader import (
    DatabaseCandidateInvestigationReader,
)


def build_database_candidate_tool_registry(session: Session) -> ToolRegistry:
    """Compose the database reader adapter and production Candidate tool."""
    return build_candidate_tool_registry(
        DatabaseCandidateInvestigationReader(session=session)
    )
