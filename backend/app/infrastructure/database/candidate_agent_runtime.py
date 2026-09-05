from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.agent.contracts import ToolEffect, ToolRisk
from app.agent.policy import ToolAuthorizationContext
from app.agent.runtime import run_candidate_investigation
from app.agent.runtime_contracts import InvestigationProvider
from app.infrastructure.database.agent_audit_persistence import (
    AgentRunAuditAggregate,
)
from app.infrastructure.database.candidate_investigation_reader import (
    DatabaseCandidateInvestigationReader,
)
from app.infrastructure.database.candidate_tool_composition import (
    build_database_candidate_tool_registry,
)


def start_database_candidate_investigation(
    session: Session,
    *,
    candidate_id: UUID,
    provider: InvestigationProvider,
) -> AgentRunAuditAggregate | None:
    """Compose and run one server-authorized Candidate investigation."""
    reader = DatabaseCandidateInvestigationReader(session=session)
    if reader.read_candidate_evidence(candidate_id) is None:
        return None

    investigation_id = uuid4()
    authorization = ToolAuthorizationContext(
        investigation_id=investigation_id,
        candidate_id=candidate_id,
        allowed_effects=frozenset({ToolEffect.READ}),
        maximum_risk=ToolRisk.LOW,
        granted_scopes=frozenset({"candidate:read"}),
    )
    return run_candidate_investigation(
        session,
        candidate_id=candidate_id,
        provider=provider,
        registry=build_database_candidate_tool_registry(session),
        authorization=authorization,
    )
