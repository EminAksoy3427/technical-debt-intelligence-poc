from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal, SourceObservationRef
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import EvidenceModel, SignalModel
from app.signal_ingestion import NormalizedSignal


class SignalPersistenceResult(StrEnum):
    CREATED = "CREATED"
    DUPLICATE = "DUPLICATE"


def persist_normalized_signal(
    session: Session,
    normalized_signal: NormalizedSignal,
) -> SignalPersistenceResult:
    """Persist one normalized Signal in the caller-owned transaction."""
    signal = normalized_signal.signal
    existing_signal_id = session.scalar(
        select(SignalModel.signal_id).where(
            SignalModel.source_system == signal.source_system,
            SignalModel.source_record_id == signal.source_record_id,
        )
    )
    if existing_signal_id is not None:
        return SignalPersistenceResult.DUPLICATE

    affected_asset = session.scalar(
        select(EnterpriseAssetModel).where(
            EnterpriseAssetModel.asset_key == signal.affected_asset.asset_key
        )
    )
    if affected_asset is None:
        raise ValueError(
            "Signal affected asset does not exist in the enterprise catalog"
        )
    if affected_asset.asset_type != signal.affected_asset.asset_type.value:
        raise ValueError(
            "Signal affected asset type does not match the enterprise catalog"
        )

    persisted_signal = SignalModel(
        signal_id=signal.signal_id,
        source_system=signal.source_system,
        source_record_id=signal.source_record_id,
        detected_at=signal.detected_at,
        signal_type=signal.signal_type,
        affected_asset=affected_asset,
        severity=signal.severity,
        evidence=[
            EvidenceModel(
                evidence_id=evidence.evidence_id,
                source_system=evidence.source_system,
                source_reference=evidence.source_reference,
                captured_at=evidence.captured_at,
                reference_uri=evidence.reference_uri,
            )
            for evidence in sorted(
                normalized_signal.evidence,
                key=lambda item: item.evidence_id.hex,
            )
        ],
    )
    session.add(persisted_signal)
    session.flush()
    return SignalPersistenceResult.CREATED


def get_normalized_signal(
    session: Session,
    provenance: SourceObservationRef,
) -> NormalizedSignal | None:
    """Reconstruct a normalized Signal from its exact source observation identity."""
    persisted_signal = session.scalar(
        select(SignalModel)
        .options(
            joinedload(SignalModel.affected_asset),
            selectinload(SignalModel.evidence),
        )
        .where(
            SignalModel.source_system == provenance.source_system,
            SignalModel.source_record_id == provenance.source_record_id,
        )
    )
    if persisted_signal is None:
        return None

    evidence = frozenset(
        Evidence(
            evidence_id=item.evidence_id,
            source_system=item.source_system,
            source_reference=item.source_reference,
            captured_at=_as_timezone_aware(item.captured_at),
            reference_uri=item.reference_uri,
        )
        for item in persisted_signal.evidence
    )
    signal = Signal(
        signal_id=persisted_signal.signal_id,
        source_system=persisted_signal.source_system,
        source_record_id=persisted_signal.source_record_id,
        detected_at=_as_timezone_aware(persisted_signal.detected_at),
        signal_type=persisted_signal.signal_type,
        affected_asset=CanonicalAssetRef(
            asset_key=persisted_signal.affected_asset.asset_key,
            asset_type=AssetType(persisted_signal.affected_asset.asset_type),
        ),
        severity=persisted_signal.severity,
        evidence_ids=frozenset(item.evidence_id for item in evidence),
    )
    return NormalizedSignal(signal=signal, evidence=evidence)


def _as_timezone_aware(value: datetime) -> datetime:
    """Preserve the domain's timezone-aware timestamp invariant."""
    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=UTC)
    return value
