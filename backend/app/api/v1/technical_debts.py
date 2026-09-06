from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_database_session
from app.api.v1.technical_debt_schemas import (
    TechnicalDebtDetailResponse,
    TechnicalDebtListResponse,
    technical_debt_detail_response,
    technical_debt_list_response,
)
from app.infrastructure.database.technical_debt_read_model import (
    TechnicalDebtReadIntegrityError,
    list_technical_debt_summaries,
    load_technical_debt_detail,
)

router = APIRouter(prefix="/technical-debts", tags=["technical-debts"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]


@router.get("", response_model=TechnicalDebtListResponse)
def get_technical_debts(session: DatabaseSession) -> TechnicalDebtListResponse:
    try:
        summaries = list_technical_debt_summaries(session)
    except TechnicalDebtReadIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted TechnicalDebt data failed integrity validation",
        ) from error
    return technical_debt_list_response(summaries)


@router.get("/{technical_debt_id}", response_model=TechnicalDebtDetailResponse)
def get_technical_debt(
    technical_debt_id: UUID,
    session: DatabaseSession,
) -> TechnicalDebtDetailResponse:
    try:
        detail = load_technical_debt_detail(session, technical_debt_id)
    except TechnicalDebtReadIntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted TechnicalDebt data failed integrity validation",
        ) from error
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TechnicalDebt not found",
        )
    return technical_debt_detail_response(detail)
