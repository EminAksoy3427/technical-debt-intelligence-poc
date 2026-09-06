from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.dependencies import get_human_actor_context, get_human_validation_session
from app.api.v1.human_decision_schemas import (
    HumanValidationRequest,
    HumanValidationResponse,
    human_validation_response,
)
from app.governance.contracts import (
    CandidateNotFound,
    GovernancePersistenceConflict,
    HumanActorContext,
    HumanValidationCommand,
    InvalidGovernanceTransition,
    InvalidHumanDecisionCommand,
    StaleGovernanceRevision,
)
from app.governance.human_validation import apply_human_validation

router = APIRouter(prefix="/candidates", tags=["candidate-human-decisions"])

HumanValidationSession = Annotated[Session, Depends(get_human_validation_session)]
ServerOwnedHumanActor = Annotated[HumanActorContext, Depends(get_human_actor_context)]


@router.post(
    "/{candidate_id}/human-decisions",
    response_model=HumanValidationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_candidate_human_decision(
    candidate_id: UUID,
    payload: HumanValidationRequest,
    session: HumanValidationSession,
    actor_context: ServerOwnedHumanActor,
) -> HumanValidationResponse:
    command = _human_validation_command(candidate_id, payload)
    try:
        result = apply_human_validation(session, command, actor_context)
    except CandidateNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidate not found",
        ) from error
    except (
        StaleGovernanceRevision,
        InvalidGovernanceTransition,
        GovernancePersistenceConflict,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except InvalidHumanDecisionCommand as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Human Validation could not be persisted",
        ) from error
    return human_validation_response(result)


def _human_validation_command(
    candidate_id: UUID,
    payload: HumanValidationRequest,
) -> HumanValidationCommand:
    try:
        return HumanValidationCommand(
            candidate_id=candidate_id,
            decision=payload.decision,
            expected_governance_revision=payload.expected_governance_revision,
            rationale=payload.rationale,
            requested_information=payload.requested_information,
        )
    except InvalidHumanDecisionCommand as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
