from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.actions.approval import approve_action_proposal
from app.actions.contracts import (
    ActionApprovalPersistenceConflict,
    ActionExecutionDoesNotBelongToProposal,
    ActionExecutionNotFound,
    ActionExecutionNotVerifiable,
    ActionExecutionReconciliationUnresolved,
    ActionPreparationContext,
    ActionProposalAlreadyApproved,
    ActionProposalDoesNotBelongToTechnicalDebt,
    ActionProposalNotFound,
    ActionProposalPersistenceConflict,
    ActionProposalSourceContextMissing,
    ActionVerificationUnavailable,
    ApproveActionProposalCommand,
    CompetingActionApprovalExists,
    ExecuteActionProposalCommand,
    InvalidActionPreparationTarget,
    LogicalActionExecutionConflict,
    PrepareActionProposalCommand,
    StaleActionProposalFingerprint,
    TechnicalDebtNotFound,
    TechnicalDebtNotRegistered,
    VerifyActionExecutionCommand,
)
from app.actions.execution import (
    ExecuteActionProposalDisposition,
    execute_action_proposal,
)
from app.actions.github_issue_executor import GitHubIssueExecutor
from app.actions.github_issue_verifier import GitHubIssueVerifier
from app.actions.preparation import prepare_action_proposal
from app.actions.verification import verify_action_execution
from app.api.dependencies import (
    ACTION_PREPARATION_UNAVAILABLE_DETAIL,
    ACTION_VERIFICATION_UNAVAILABLE_DETAIL,
    get_action_approval_actor_context,
    get_action_approval_session,
    get_action_execution_session,
    get_action_preparation_actor_context,
    get_action_preparation_context,
    get_action_preparation_session,
    get_action_verification_session,
    get_database_session,
    get_github_issue_executor,
    get_github_issue_verifier,
)
from app.api.v1.technical_debt_schemas import (
    ActionApprovalResponse,
    ActionExecutionResponse,
    ActionProposalResponse,
    ActionVerificationResponse,
    ApproveActionProposalRequest,
    TechnicalDebtDetailResponse,
    TechnicalDebtListResponse,
    action_approval_response,
    action_execution_response,
    action_proposal_response,
    action_verification_response,
    technical_debt_detail_response,
    technical_debt_list_response,
)
from app.core.config import settings
from app.governance.contracts import HumanActorContext
from app.infrastructure.database.technical_debt_read_model import (
    TechnicalDebtReadIntegrityError,
    list_technical_debt_summaries,
    load_technical_debt_detail,
)

router = APIRouter(prefix="/technical-debts", tags=["technical-debts"])

DatabaseSession = Annotated[Session, Depends(get_database_session)]
ActionPreparationSession = Annotated[Session, Depends(get_action_preparation_session)]
ActionApprovalSession = Annotated[Session, Depends(get_action_approval_session)]
ActionExecutionSession = Annotated[Session, Depends(get_action_execution_session)]
ActionVerificationSession = Annotated[
    Session, Depends(get_action_verification_session)
]
ServerGitHubIssueExecutor = Annotated[
    GitHubIssueExecutor | None,
    Depends(get_github_issue_executor),
]
ServerGitHubIssueVerifier = Annotated[
    GitHubIssueVerifier | None,
    Depends(get_github_issue_verifier),
]
ActionPreparationActor = Annotated[
    HumanActorContext,
    Depends(get_action_preparation_actor_context),
]
ActionApprovalActor = Annotated[
    HumanActorContext,
    Depends(get_action_approval_actor_context),
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


@router.post(
    "/{technical_debt_id}/action-proposals/{action_proposal_id}/approvals",
    response_model=ActionApprovalResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_technical_debt_action_proposal_approval(
    technical_debt_id: UUID,
    action_proposal_id: UUID,
    payload: ApproveActionProposalRequest,
    session: ActionApprovalSession,
    actor_context: ActionApprovalActor,
) -> ActionApprovalResponse:
    command = ApproveActionProposalCommand(
        technical_debt_id=technical_debt_id,
        action_proposal_id=action_proposal_id,
        expected_payload_fingerprint=payload.expected_payload_fingerprint,
    )
    try:
        approval = approve_action_proposal(session, command, actor_context)
    except TechnicalDebtNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TechnicalDebt not found",
        ) from error
    except (
        ActionProposalNotFound,
        ActionProposalDoesNotBelongToTechnicalDebt,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ActionProposal not found",
        ) from error
    except StaleActionProposalFingerprint as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "expected_payload_fingerprint does not match the persisted "
                "ActionProposal"
            ),
        ) from error
    except ActionProposalAlreadyApproved as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ActionProposal is already approved",
        ) from error
    except CompetingActionApprovalExists as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "A competing ActionProposal already holds approval for this "
                "logical action"
            ),
        ) from error
    except ActionApprovalPersistenceConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ActionApproval could not be persisted because of a conflict",
        ) from error
    except IntegrityError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ActionApproval could not be persisted",
        ) from error
    return action_approval_response(approval)


@router.post(
    "/{technical_debt_id}/action-proposals/{action_proposal_id}/executions",
    response_model=ActionExecutionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_technical_debt_action_proposal_execution(
    technical_debt_id: UUID,
    action_proposal_id: UUID,
    request: Request,
    response: Response,
    session: ActionExecutionSession,
    preparation_context: ServerOwnedPreparationContext,
    executor: ServerGitHubIssueExecutor,
) -> ActionExecutionResponse:
    if await request.body():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Request body is not supported",
        )
    try:
        result = execute_action_proposal(
            session,
            ExecuteActionProposalCommand(
                technical_debt_id=technical_debt_id,
                action_proposal_id=action_proposal_id,
            ),
            preparation_context,
            settings.human_action_execution_enabled,
            executor,
        )
    except TechnicalDebtNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TechnicalDebt not found",
        ) from error
    except (
        ActionProposalNotFound,
        ActionProposalDoesNotBelongToTechnicalDebt,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ActionProposal not found",
        ) from error
    except LogicalActionExecutionConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another proposal occupies this logical external action",
        ) from error

    if result.disposition is ExecuteActionProposalDisposition.DENIED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Action execution policy denied this proposal",
        )
    if result.disposition is ExecuteActionProposalDisposition.EXISTING:
        response.status_code = status.HTTP_200_OK
    assert result.execution is not None
    return action_execution_response(result.execution)


@router.post(
    "/{technical_debt_id}/action-proposals/{action_proposal_id}"
    "/executions/{action_execution_id}/verifications",
    response_model=ActionVerificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_technical_debt_action_execution_verification(
    technical_debt_id: UUID,
    action_proposal_id: UUID,
    action_execution_id: UUID,
    request: Request,
    session: ActionVerificationSession,
    preparation_context: ServerOwnedPreparationContext,
    verifier: ServerGitHubIssueVerifier,
) -> ActionVerificationResponse:
    if await request.body():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Request body is not supported",
        )
    try:
        verification = verify_action_execution(
            session,
            VerifyActionExecutionCommand(
                technical_debt_id=technical_debt_id,
                action_proposal_id=action_proposal_id,
                action_execution_id=action_execution_id,
            ),
            preparation_context,
            verifier,
        )
    except TechnicalDebtNotFound as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="TechnicalDebt not found",
        ) from error
    except (
        ActionProposalNotFound,
        ActionProposalDoesNotBelongToTechnicalDebt,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ActionProposal not found",
        ) from error
    except (
        ActionExecutionNotFound,
        ActionExecutionDoesNotBelongToProposal,
    ) as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ActionExecution not found",
        ) from error
    except ActionExecutionNotVerifiable as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ActionExecution is not verifiable",
        ) from error
    except ActionExecutionReconciliationUnresolved as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error
    except ActionVerificationUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ACTION_VERIFICATION_UNAVAILABLE_DETAIL,
        ) from error
    return action_verification_response(verification)
