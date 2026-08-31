from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.api.v1.candidate_schemas import (
    CandidateDetailResponse,
    CandidateListResponse,
    candidate_detail_response,
    candidate_list_response,
)
from app.infrastructure.database.candidate_read_model import (
    CandidateReadIntegrityError,
    list_candidate_summaries,
    load_candidate_detail,
)

router = APIRouter(prefix="/candidates", tags=["candidates"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=CandidateListResponse)
def get_candidates(session: DatabaseSession) -> CandidateListResponse:
    try:
        summaries = list_candidate_summaries(session)
    except CandidateReadIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted Candidate data failed integrity validation",
        ) from error
    return candidate_list_response(summaries)


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate(
    candidate_id: UUID,
    session: DatabaseSession,
) -> CandidateDetailResponse:
    try:
        detail = load_candidate_detail(session, candidate_id)
    except CandidateReadIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted Candidate data failed integrity validation",
        ) from error
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        )
    return candidate_detail_response(detail)
