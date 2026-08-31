from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.candidate_enterprise_context import CandidateEnterpriseContext
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database.candidate_dependency_context import (
    CandidateDependencyContextIntegrityError,
    load_candidate_dependency_context,
)
from app.infrastructure.database.candidate_enterprise_context import (
    CandidateEnterpriseContextIntegrityError,
    load_candidate_enterprise_context,
)
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.candidate_persistence import load_candidate
from app.infrastructure.database.signal_models import SignalModel


class CandidateReadIntegrityError(ValueError):
    """Persisted Candidate facts cannot form the public read model."""


@dataclass(frozen=True)
class CandidateSummary:
    candidate: Candidate
    enterprise_context: CandidateEnterpriseContext


@dataclass(frozen=True)
class CandidateDetail:
    candidate: Candidate
    signals: tuple[Signal, ...]
    evidence: tuple[Evidence, ...]
    enterprise_context: CandidateEnterpriseContext
    dependency_context: CandidateDependencyContext


def list_candidate_summaries(session: Session) -> tuple[CandidateSummary, ...]:
    """Load all Candidate summaries in stable factual order."""
    with session.no_autoflush:
        candidate_ids = tuple(session.scalars(select(CandidateModel.candidate_id)))
        summaries = tuple(
            _load_candidate_summary(session, item) for item in candidate_ids
        )

    return tuple(
        sorted(
            summaries,
            key=lambda item: (
                item.candidate.canonical_asset.asset_key,
                item.candidate.hypothesis,
                item.candidate.candidate_id.hex,
            ),
        )
    )


def load_candidate_detail(
    session: Session,
    candidate_id: UUID,
) -> CandidateDetail | None:
    """Load one complete, deterministic Candidate read model."""
    with session.no_autoflush:
        try:
            candidate = load_candidate(session, candidate_id)
            if candidate is None:
                return None
            signals, evidence = _load_signals_and_evidence(session, candidate)
            enterprise_context = load_candidate_enterprise_context(
                session,
                candidate_id,
            )
            dependency_context = load_candidate_dependency_context(
                session,
                candidate_id,
            )
        except (
            CandidateDependencyContextIntegrityError,
            CandidateEnterpriseContextIntegrityError,
            ValueError,
        ) as error:
            raise CandidateReadIntegrityError(
                "Persisted Candidate facts are inconsistent"
            ) from error

    if enterprise_context is None or dependency_context is None:
        raise CandidateReadIntegrityError(
            "Persisted Candidate context is unexpectedly missing"
        )

    return CandidateDetail(
        candidate=candidate,
        signals=signals,
        evidence=evidence,
        enterprise_context=enterprise_context,
        dependency_context=dependency_context,
    )


def _load_candidate_summary(
    session: Session,
    candidate_id: UUID,
) -> CandidateSummary:
    try:
        candidate = load_candidate(session, candidate_id)
        if candidate is None:
            raise CandidateReadIntegrityError(
                "Persisted Candidate disappeared during summary assembly"
            )
        _load_signals_and_evidence(session, candidate)
        enterprise_context = load_candidate_enterprise_context(session, candidate_id)
    except (CandidateEnterpriseContextIntegrityError, ValueError) as error:
        raise CandidateReadIntegrityError(
            "Persisted Candidate facts are inconsistent"
        ) from error

    if enterprise_context is None:
        raise CandidateReadIntegrityError(
            "Persisted Candidate enterprise context is unexpectedly missing"
        )
    return CandidateSummary(
        candidate=candidate,
        enterprise_context=enterprise_context,
    )


def _load_signals_and_evidence(
    session: Session,
    candidate: Candidate,
) -> tuple[tuple[Signal, ...], tuple[Evidence, ...]]:
    persisted_signals = tuple(
        session.scalars(
            select(SignalModel)
            .options(
                joinedload(SignalModel.affected_asset),
                selectinload(SignalModel.evidence),
            )
            .where(SignalModel.signal_id.in_(candidate.signal_ids))
        )
    )
    if {item.signal_id for item in persisted_signals} != set(candidate.signal_ids):
        raise CandidateReadIntegrityError(
            "Candidate Signal membership references missing persisted Signals"
        )

    signals: list[Signal] = []
    evidence_by_id: dict[UUID, Evidence] = {}
    for persisted_signal in persisted_signals:
        affected_asset = CanonicalAssetRef(
            asset_key=persisted_signal.affected_asset.asset_key,
            asset_type=AssetType(persisted_signal.affected_asset.asset_type),
        )
        if affected_asset != candidate.canonical_asset:
            raise CandidateReadIntegrityError(
                "Candidate Signal asset does not match the Candidate asset"
            )

        signal_evidence_ids: set[UUID] = set()
        for persisted_evidence in persisted_signal.evidence:
            evidence = Evidence(
                evidence_id=persisted_evidence.evidence_id,
                source_system=persisted_evidence.source_system,
                source_reference=persisted_evidence.source_reference,
                captured_at=_as_timezone_aware(persisted_evidence.captured_at),
                reference_uri=persisted_evidence.reference_uri,
            )
            existing = evidence_by_id.get(evidence.evidence_id)
            if existing is not None and existing != evidence:
                raise CandidateReadIntegrityError(
                    "Candidate Evidence identity has conflicting persisted facts"
                )
            evidence_by_id[evidence.evidence_id] = evidence
            signal_evidence_ids.add(evidence.evidence_id)

        signals.append(
            Signal(
                signal_id=persisted_signal.signal_id,
                source_system=persisted_signal.source_system,
                source_record_id=persisted_signal.source_record_id,
                detected_at=_as_timezone_aware(persisted_signal.detected_at),
                signal_type=persisted_signal.signal_type,
                affected_asset=affected_asset,
                severity=persisted_signal.severity,
                evidence_ids=frozenset(signal_evidence_ids),
            )
        )

    if set(evidence_by_id) != set(candidate.evidence_ids):
        raise CandidateReadIntegrityError(
            "Candidate Evidence union does not match linked Signal Evidence"
        )

    return (
        tuple(sorted(signals, key=lambda item: (item.detected_at, item.signal_id.hex))),
        tuple(
            sorted(
                evidence_by_id.values(),
                key=lambda item: (item.captured_at, item.evidence_id.hex),
            )
        ),
    )


def _as_timezone_aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
