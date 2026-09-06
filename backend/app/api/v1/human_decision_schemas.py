from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.human_decisions import HumanDecision, HumanDecisionType
from app.domain.technical_debts import TechnicalDebt, TechnicalDebtLifecycleStatus
from app.governance.contracts import CandidateGovernanceState
from app.governance.human_validation import AppliedHumanValidation


class HumanValidationApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class HumanValidationRequest(HumanValidationApiModel):
    """Untrusted Human Validation intent. Actor identity is server-owned."""

    decision: HumanDecisionType
    rationale: str | None = None
    requested_information: str | None = None
    expected_governance_revision: int = Field(ge=0)


class HumanDecisionResponse(HumanValidationApiModel):
    human_decision_id: UUID
    candidate_id: UUID
    sequence_number: int
    decision: HumanDecisionType
    rationale: str | None
    requested_information: str | None
    actor_reference: str
    created_at: datetime


class HumanValidationGovernanceResponse(HumanValidationApiModel):
    state: CandidateGovernanceState
    revision: int


class HumanValidationTechnicalDebtResponse(HumanValidationApiModel):
    technical_debt_id: UUID
    lifecycle_status: TechnicalDebtLifecycleStatus
    created_at: datetime
    source_candidate_id: UUID


class HumanValidationResponse(HumanValidationApiModel):
    human_decision: HumanDecisionResponse
    governance: HumanValidationGovernanceResponse
    technical_debt: HumanValidationTechnicalDebtResponse | None


def human_validation_response(
    result: AppliedHumanValidation,
) -> HumanValidationResponse:
    return HumanValidationResponse(
        human_decision=_human_decision_response(result.human_decision),
        governance=HumanValidationGovernanceResponse(
            state=result.governance.state,
            revision=result.governance.revision,
        ),
        technical_debt=_technical_debt_response(result.technical_debt),
    )


def _human_decision_response(decision: HumanDecision) -> HumanDecisionResponse:
    return HumanDecisionResponse(
        human_decision_id=decision.human_decision_id,
        candidate_id=decision.candidate_id,
        sequence_number=decision.sequence_number,
        decision=decision.decision_type,
        rationale=decision.rationale,
        requested_information=decision.requested_information,
        actor_reference=decision.actor_reference,
        created_at=decision.created_at,
    )


def _technical_debt_response(
    technical_debt: TechnicalDebt | None,
) -> HumanValidationTechnicalDebtResponse | None:
    if technical_debt is None:
        return None
    return HumanValidationTechnicalDebtResponse(
        technical_debt_id=technical_debt.technical_debt_id,
        lifecycle_status=technical_debt.lifecycle_status,
        created_at=technical_debt.created_at,
        source_candidate_id=technical_debt.source_candidate_id,
    )
