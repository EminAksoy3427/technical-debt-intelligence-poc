from enum import StrEnum
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.infrastructure.database.candidate_models import (
    CandidateModel,
    CandidateSignalModel,
)
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel


class CandidatePersistenceResult(StrEnum):
    CREATED = "CREATED"
    UPDATED = "UPDATED"
    UNCHANGED = "UNCHANGED"


def persist_candidate(
    session: Session,
    candidate: Candidate,
) -> CandidatePersistenceResult:
    """Persist a Candidate snapshot in the caller-owned transaction."""
    signals = _load_candidate_signals(session, candidate)
    canonical_asset = _load_canonical_asset(session, candidate)
    _verify_signal_assets(candidate, signals)
    _verify_evidence_ids(session, candidate)

    persisted_candidate = session.scalar(
        select(CandidateModel)
        .options(
            joinedload(CandidateModel.canonical_asset),
            selectinload(CandidateModel.signal_memberships),
        )
        .where(CandidateModel.candidate_id == candidate.candidate_id)
    )
    if persisted_candidate is None:
        session.add(
            CandidateModel(
                candidate_id=candidate.candidate_id,
                canonical_asset=canonical_asset,
                hypothesis=candidate.hypothesis,
                correlation_rationale=candidate.correlation_rationale,
                signal_memberships=[
                    CandidateSignalModel(signal_id=signal_id)
                    for signal_id in sorted(
                        candidate.signal_ids,
                        key=lambda item: item.hex,
                    )
                ],
            )
        )
        session.flush()
        return CandidatePersistenceResult.CREATED

    if not _assets_match(persisted_candidate.canonical_asset, candidate):
        raise ValueError(
            "Candidate canonical asset conflicts with the persisted candidate identity"
        )

    existing_signal_ids = frozenset(
        membership.signal_id for membership in persisted_candidate.signal_memberships
    )
    if (
        existing_signal_ids == candidate.signal_ids
        and persisted_candidate.hypothesis == candidate.hypothesis
        and persisted_candidate.correlation_rationale == candidate.correlation_rationale
    ):
        return CandidatePersistenceResult.UNCHANGED

    persisted_candidate.hypothesis = candidate.hypothesis
    persisted_candidate.correlation_rationale = candidate.correlation_rationale
    persisted_candidate.signal_memberships = [
        CandidateSignalModel(signal_id=signal_id)
        for signal_id in sorted(candidate.signal_ids, key=lambda item: item.hex)
    ]
    session.flush()
    return CandidatePersistenceResult.UPDATED


def load_candidate(session: Session, candidate_id: UUID) -> Candidate | None:
    """Reconstruct a Candidate from persisted snapshot and Signal Evidence."""
    persisted_candidate = session.scalar(
        select(CandidateModel)
        .options(
            joinedload(CandidateModel.canonical_asset),
            selectinload(CandidateModel.signal_memberships),
        )
        .where(CandidateModel.candidate_id == candidate_id)
    )
    if persisted_candidate is None:
        return None

    signal_ids = frozenset(
        membership.signal_id for membership in persisted_candidate.signal_memberships
    )
    evidence_ids = _evidence_ids_for_signals(session, signal_ids)
    return Candidate(
        candidate_id=persisted_candidate.candidate_id,
        signal_ids=signal_ids,
        evidence_ids=evidence_ids,
        canonical_asset=CanonicalAssetRef(
            asset_key=persisted_candidate.canonical_asset.asset_key,
            asset_type=AssetType(persisted_candidate.canonical_asset.asset_type),
        ),
        hypothesis=persisted_candidate.hypothesis,
        correlation_rationale=persisted_candidate.correlation_rationale,
    )


def _load_candidate_signals(
    session: Session,
    candidate: Candidate,
) -> tuple[SignalModel, ...]:
    signals = tuple(
        session.scalars(
            select(SignalModel)
            .options(joinedload(SignalModel.affected_asset))
            .where(SignalModel.signal_id.in_(candidate.signal_ids))
        )
    )
    persisted_signal_ids = frozenset(signal.signal_id for signal in signals)
    unknown_signal_ids = candidate.signal_ids - persisted_signal_ids
    if unknown_signal_ids:
        raise ValueError("Candidate references Signal IDs that are not persisted")
    return signals


def _load_canonical_asset(
    session: Session,
    candidate: Candidate,
) -> EnterpriseAssetModel:
    canonical_asset = session.scalar(
        select(EnterpriseAssetModel).where(
            EnterpriseAssetModel.asset_key == candidate.canonical_asset.asset_key
        )
    )
    if canonical_asset is None:
        raise ValueError(
            "Candidate canonical asset does not exist in the enterprise catalog"
        )
    if canonical_asset.asset_type != candidate.canonical_asset.asset_type.value:
        raise ValueError(
            "Candidate canonical asset type does not match the enterprise catalog"
        )
    return canonical_asset


def _verify_signal_assets(
    candidate: Candidate,
    signals: tuple[SignalModel, ...],
) -> None:
    if any(not _assets_match(signal.affected_asset, candidate) for signal in signals):
        raise ValueError("Candidate Signals must match the Candidate canonical asset")


def _verify_evidence_ids(session: Session, candidate: Candidate) -> None:
    persisted_evidence_ids = _evidence_ids_for_signals(session, candidate.signal_ids)
    if candidate.evidence_ids != persisted_evidence_ids:
        raise ValueError(
            "Candidate Evidence IDs do not match the linked Signals' persisted Evidence"
        )


def _evidence_ids_for_signals(
    session: Session,
    signal_ids: frozenset[UUID],
) -> frozenset[UUID]:
    return frozenset(
        session.scalars(
            select(EvidenceModel.evidence_id).where(
                EvidenceModel.signal_id.in_(signal_ids)
            )
        )
    )


def _assets_match(
    persisted_asset: EnterpriseAssetModel,
    candidate: Candidate,
) -> bool:
    return (
        persisted_asset.asset_key == candidate.canonical_asset.asset_key
        and persisted_asset.asset_type == candidate.canonical_asset.asset_type.value
    )
