from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.contracts import (
    ActionPreparationContext,
    ActionProposalPersistenceConflict,
    ActionProposalSourceContextMissing,
    InvalidActionPreparationTarget,
    PrepareActionProposalCommand,
    TechnicalDebtNotFound,
    TechnicalDebtNotRegistered,
)
from app.actions.preparation import prepare_action_proposal
from app.api.dependencies import (
    ACTION_PREPARATION_UNAVAILABLE_DETAIL,
    get_action_preparation_actor_context,
    get_action_preparation_context,
    get_action_preparation_session,
    get_database_session,
)
from app.api.v1.technical_debt_schemas import (
    ActionProposalResponse,
    TechnicalDebtDetailResponse,
    TechnicalDebtListResponse,
    action_proposal_response,
    technical_debt_detail_response,
    technical_debt_list_response,
)
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.technical_debt_read_model import (
    TechnicalDebtReadIntegrityError,
    list_technical_debt_summaries,
    load_technical_debt_detail,
)

router = APIRouter(prefix="/technical-debts", tags=["technical-debts"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ActionPreparationSession = Annotated[Session, Depends(get_action_preparation_session)]
ActionPreparationActor = Annotated[
    HumanActorContext,
    Depends(get_action_preparation_actor_context),
]
ServerOwnedPreparationContext = Annotated[
    ActionPreparationContext,
    Depends(get_action_preparation_context),
]


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


@router.post(
    "/{technical_debt_id}/action-proposals",
    response_model=ActionProposalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_technical_debt_action_proposal(
    technical_debt_id: UUID,
    request: Request,
    session: ActionPreparationSession,
    actor_context: ActionPreparationActor,
    preparation_context: ServerOwnedPreparationContext,
) -> ActionProposalResponse:
    if await request.body():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Request body is not supported",
        )

    command = PrepareActionProposalCommand(technical_debt_id=technical_debt_id)
    try:
        proposal = prepare_action_proposal(
            session,
            command,
            actor_context,
            preparation_context,
        )
    except TechnicalDebtNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TechnicalDebt not found",
        ) from error
    except TechnicalDebtNotRegistered as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="TechnicalDebt is not REGISTERED",
        ) from error
    except InvalidActionPreparationTarget as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=ACTION_PREPARATION_UNAVAILABLE_DETAIL,
        ) from error
    except ActionProposalSourceContextMissing as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Persisted TechnicalDebt data failed integrity validation",
        ) from error
    except ActionProposalPersistenceConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ActionProposal could not be persisted because of a conflict",
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ActionProposal could not be persisted",
        ) from error
    return action_proposal_response(proposal)
