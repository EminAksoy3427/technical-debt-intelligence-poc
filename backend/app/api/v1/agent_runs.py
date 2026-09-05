from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.agent.runtime_contracts import InvestigationProvider
from app.api.dependencies import (
    get_candidate_investigation_provider,
    get_database_session,
)
from app.api.v1.agent_run_schemas import AgentRunResponse, agent_run_response
from app.infrastructure.database.agent_audit_persistence import (
    load_candidate_agent_run_audit,
)
from app.infrastructure.database.candidate_agent_runtime import (
    start_database_candidate_investigation,
)
from app.infrastructure.database.candidate_read_model import (
    CandidateReadIntegrityError,
)

router = APIRouter(prefix="/candidates", tags=["candidate-agent-runs"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
CandidateInvestigationProvider = Annotated[
    InvestigationProvider,
    Depends(get_candidate_investigation_provider),
]


@router.post(
    "/{candidate_id}/agent-runs",
    response_model=AgentRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_candidate_agent_run(
    candidate_id: UUID,
    request: Request,
    session: DatabaseSession,
    provider: CandidateInvestigationProvider,
) -> AgentRunResponse:
    if await request.body():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Request body is not supported",
        )

    try:
        aggregate = start_database_candidate_investigation(
            session,
            candidate_id=candidate_id,
            provider=provider,
        )
    except CandidateReadIntegrityError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted Candidate data failed integrity validation",
        ) from error
    except Exception as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent investigation could not be started",
        ) from error

    if aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return agent_run_response(aggregate)


@router.get(
    "/{candidate_id}/agent-runs/{agent_run_id}",
    response_model=AgentRunResponse,
)
def get_candidate_agent_run(
    candidate_id: UUID,
    agent_run_id: UUID,
    session: DatabaseSession,
) -> AgentRunResponse:
    try:
        aggregate = load_candidate_agent_run_audit(
            session,
            candidate_id=candidate_id,
            agent_run_id=agent_run_id,
        )
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted AgentRun data failed integrity validation",
        ) from error
    if aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AgentRun not found",
        )
    return agent_run_response(aggregate)
