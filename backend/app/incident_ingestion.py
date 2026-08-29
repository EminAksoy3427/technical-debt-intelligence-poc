from typing import Final
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import Incident
from app.domain.signals import Evidence, Signal
from app.signal_ingestion import NormalizedSignal

INCIDENT_SOURCE_SYSTEM: Final = "incident-management"
INCIDENT_SIGNAL_TYPE: Final = "OPERATIONAL_INCIDENT"

_SIGNAL_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/incident/signal",
)
_EVIDENCE_ID_NAMESPACE = uuid5(
    NAMESPACE_URL,
    "technical-debt-intelligence-poc/incident/evidence",
)


def normalize_incident(
    incident: Incident,
    *,
    primary_affected_asset: CanonicalAssetRef,
) -> NormalizedSignal:
    """Map one Incident to a canonical Signal using its stable source facts.

    ``started_at`` represents when the incident observation began, so it is used
    unchanged for both Signal detection and Evidence capture timestamps.
    """
    if primary_affected_asset.asset_key != incident.primary_affected_asset_key:
        raise ValueError(
            "Incident primary affected asset must match the supplied asset reference"
        )

    source_record_id = incident.incident_key
    signal_id = _stable_id(_SIGNAL_ID_NAMESPACE, source_record_id)
    evidence_id = _stable_id(_EVIDENCE_ID_NAMESPACE, source_record_id)
    evidence = Evidence(
        evidence_id=evidence_id,
        source_system=INCIDENT_SOURCE_SYSTEM,
        source_reference=(
            f"{incident.incident_key}: {incident.title} "
            f"(affected asset: {primary_affected_asset.asset_key})"
        ),
        captured_at=incident.started_at,
        reference_uri=None,
    )
    signal = Signal(
        signal_id=signal_id,
        source_system=INCIDENT_SOURCE_SYSTEM,
        source_record_id=source_record_id,
        detected_at=incident.started_at,
        signal_type=INCIDENT_SIGNAL_TYPE,
        affected_asset=primary_affected_asset,
        severity=incident.severity.value,
        evidence_ids=frozenset({evidence_id}),
    )
    return NormalizedSignal(signal=signal, evidence=frozenset({evidence}))


def _stable_id(namespace: UUID, source_record_id: str) -> UUID:
    return uuid5(namespace, f"{INCIDENT_SOURCE_SYSTEM}:{source_record_id}")
