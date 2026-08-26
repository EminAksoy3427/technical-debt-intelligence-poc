from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.signals import Evidence, Signal


def create_evidence(
    *,
    source_system: str = "semgrep",
    source_reference: str = "finding-42",
    captured_at: datetime | None = None,
) -> Evidence:
    return Evidence(
        evidence_id=uuid4(),
        source_system=source_system,
        source_reference=source_reference,
        captured_at=(
            captured_at
            if captured_at is not None
            else datetime(2026, 8, 26, 10, 30, tzinfo=UTC)
        ),
        reference_uri="https://findings.example/finding-42",
    )


def create_signal(
    *,
    source_system: str = "semgrep",
    source_record_id: str = "finding-42",
    signal_type: str = "python.lang.security.audit",
    detected_at: datetime | None = None,
) -> Signal:
    return Signal(
        signal_id=uuid4(),
        source_system=source_system,
        source_record_id=source_record_id,
        detected_at=(
            detected_at
            if detected_at is not None
            else datetime(2026, 8, 26, 10, 35, tzinfo=UTC)
        ),
        signal_type=signal_type,
        severity="high",
        asset_hint="repository/backend",
        evidence_ids=frozenset({uuid4()}),
    )


def test_evidence_preserves_source_provenance() -> None:
    evidence = Evidence(
        evidence_id=uuid4(),
        source_system="semgrep",
        source_reference="finding-42",
        captured_at=datetime(2026, 8, 26, 10, 30, tzinfo=UTC),
        reference_uri="https://findings.example/finding-42",
    )

    assert evidence.source_system == "semgrep"
    assert evidence.source_reference == "finding-42"
    assert evidence.reference_uri == "https://findings.example/finding-42"


def test_valid_signal_retains_provenance_and_evidence_ids() -> None:
    evidence_ids = frozenset({uuid4(), uuid4()})

    signal = Signal(
        signal_id=uuid4(),
        source_system="semgrep",
        source_record_id="finding-42",
        detected_at=datetime(2026, 8, 26, 10, 35, tzinfo=UTC),
        signal_type="python.lang.security.audit",
        severity="high",
        asset_hint="repository/backend",
        evidence_ids=evidence_ids,
    )

    assert signal.source_system == "semgrep"
    assert signal.source_record_id == "finding-42"
    assert signal.evidence_ids == evidence_ids


@pytest.mark.parametrize(
    ("source_system", "source_reference", "match"),
    [
        ("  ", "finding-42", "source system"),
        ("semgrep", "\t", "source reference"),
    ],
)
def test_evidence_rejects_blank_provenance_fields(
    source_system: str,
    source_reference: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        create_evidence(
            source_system=source_system,
            source_reference=source_reference,
        )


def test_evidence_rejects_timezone_naive_captured_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_evidence(captured_at=datetime(2026, 8, 26, 10, 30))


@pytest.mark.parametrize(
    ("source_system", "source_record_id", "signal_type", "match"),
    [
        ("  ", "finding-42", "python.lang.security.audit", "source system"),
        ("semgrep", " ", "python.lang.security.audit", "source record identifier"),
        ("semgrep", "finding-42", "\t", "Signal type"),
    ],
)
def test_signal_rejects_blank_provenance_fields(
    source_system: str,
    source_record_id: str,
    signal_type: str,
    match: str,
) -> None:
    with pytest.raises(ValueError, match=match):
        create_signal(
            source_system=source_system,
            source_record_id=source_record_id,
            signal_type=signal_type,
        )


def test_signal_rejects_timezone_naive_detected_at() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        create_signal(detected_at=datetime(2026, 8, 26, 10, 35))
