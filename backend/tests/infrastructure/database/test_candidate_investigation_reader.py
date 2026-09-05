from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import AssetType
from app.domain.signals import Evidence, Signal
from app.infrastructure.database import candidate_investigation_reader as reader_module
from app.infrastructure.database.candidate_investigation_reader import (
    DatabaseCandidateInvestigationReader,
)
from app.infrastructure.database.candidate_read_model import CandidateDetail

CANDIDATE_ID = UUID("10000000-0000-0000-0000-000000000001")
SIGNAL_ID = UUID("20000000-0000-0000-0000-000000000001")
EVIDENCE_ID = UUID("30000000-0000-0000-0000-000000000001")


def _detail() -> CandidateDetail:
    asset = CanonicalAssetRef(
        asset_key="service:checkout",
        asset_type=AssetType.SERVICE,
    )
    evidence = Evidence(
        evidence_id=EVIDENCE_ID,
        source_system="semgrep",
        source_reference="src/checkout.py:42",
        captured_at=datetime(2026, 9, 1, 9, 1, tzinfo=UTC),
        reference_uri="repo://checkout/src/checkout.py#L42",
    )
    signal = Signal(
        signal_id=SIGNAL_ID,
        source_system="semgrep",
        source_record_id="finding-42",
        detected_at=datetime(2026, 9, 1, 9, 0, tzinfo=UTC),
        signal_type="MISSING_TIMEOUT",
        affected_asset=asset,
        severity="MEDIUM",
        evidence_ids=frozenset({EVIDENCE_ID}),
    )
    candidate = Candidate(
        candidate_id=CANDIDATE_ID,
        signal_ids=frozenset({SIGNAL_ID}),
        evidence_ids=frozenset({EVIDENCE_ID}),
        canonical_asset=asset,
        hypothesis="Checkout may lack a request timeout.",
        correlation_rationale="One source observation supports this hypothesis.",
    )
    return CandidateDetail(
        candidate=candidate,
        signals=(signal,),
        evidence=(evidence,),
        enterprise_context=cast(Any, object()),
        dependency_context=cast(Any, object()),
    )


def test_adapter_delegates_to_existing_candidate_detail_read_and_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    detail = _detail()
    calls: list[tuple[Session, UUID]] = []

    def load_candidate_detail(
        received_session: Session,
        candidate_id: UUID,
    ) -> CandidateDetail:
        calls.append((received_session, candidate_id))
        return detail

    monkeypatch.setattr(reader_module, "load_candidate_detail", load_candidate_detail)
    reader = DatabaseCandidateInvestigationReader(session=session)

    investigation = reader.read_candidate_evidence(CANDIDATE_ID)

    assert calls == [(session, CANDIDATE_ID)]
    assert investigation is not None
    assert investigation.candidate_id == CANDIDATE_ID
    assert investigation.asset_key == "service:checkout"
    assert investigation.asset_type is AssetType.SERVICE
    assert investigation.hypothesis == detail.candidate.hypothesis
    assert investigation.correlation_rationale == (
        detail.candidate.correlation_rationale
    )
    assert investigation.signals[0].signal_id == SIGNAL_ID
    assert investigation.signals[0].source_system == "semgrep"
    assert investigation.signals[0].source_record_id == "finding-42"
    assert investigation.signals[0].evidence_ids == (EVIDENCE_ID,)
    assert investigation.evidence[0].evidence_id == EVIDENCE_ID
    assert investigation.evidence[0].source_reference == "src/checkout.py:42"
    assert (
        investigation.evidence[0].reference_uri
        == "repo://checkout/src/checkout.py#L42"
    )
    assert not hasattr(investigation, "enterprise_context")
    assert not hasattr(investigation, "dependency_context")


def test_adapter_preserves_unknown_candidate_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    monkeypatch.setattr(
        reader_module,
        "load_candidate_detail",
        lambda _session, _candidate_id: None,
    )

    assert (
        DatabaseCandidateInvestigationReader(session).read_candidate_evidence(
            CANDIDATE_ID
        )
        is None
    )
