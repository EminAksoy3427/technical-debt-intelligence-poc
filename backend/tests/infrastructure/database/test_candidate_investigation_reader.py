from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.candidate_enterprise_context import (
    CandidateEnterpriseContext,
    EnterpriseAssetOwnership,
)
from app.domain.candidates import Candidate
from app.domain.enterprise_estate import (
    AssetCriticality,
    AssetLifecycleStatus,
    AssetOwnership,
    AssetRelationship,
    AssetRelationshipType,
    AssetType,
    EnterpriseAsset,
    Incident,
    IncidentSeverity,
    OwnershipRole,
    Team,
)
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


def _dependency_context() -> CandidateDependencyContext:
    catalog = CanonicalAssetRef(
        asset_key="svc-orbit-catalog",
        asset_type=AssetType.SERVICE,
    )
    editor = CanonicalAssetRef(
        asset_key="svc-asteria-editor",
        asset_type=AssetType.SERVICE,
    )
    renderer = CanonicalAssetRef(
        asset_key="svc-borealis-renderer",
        asset_type=AssetType.SERVICE,
    )
    return CandidateDependencyContext(
        candidate_id=CANDIDATE_ID,
        candidate_asset=CanonicalAssetRef(
            asset_key="app-asteria-canvas",
            asset_type=AssetType.APPLICATION,
        ),
        dependency_anchors=(editor, catalog),
        direct_dependencies=(catalog,),
        direct_dependents=(editor, renderer),
        reachable_dependents=(renderer,),
    )


def _enterprise_context() -> CandidateEnterpriseContext:
    return CandidateEnterpriseContext(
        candidate_id=CANDIDATE_ID,
        enterprise_asset=EnterpriseAsset(
            asset_key="svc-orbit-catalog",
            asset_type=AssetType.SERVICE,
            name="Orbit Catalog",
            criticality=AssetCriticality.HIGH,
            lifecycle_status=AssetLifecycleStatus.ACTIVE,
        ),
        enterprise_ownerships=(
            EnterpriseAssetOwnership(
                asset_ownership=AssetOwnership(
                    asset_key="svc-orbit-catalog",
                    team_key="team-orbit",
                    ownership_role=OwnershipRole.PRIMARY,
                ),
                team=Team(team_key="team-orbit", name="Orbit Platform Team"),
            ),
        ),
        direct_relationships=(
            AssetRelationship(
                source_asset_key="app-asteria-canvas",
                target_asset_key="svc-orbit-catalog",
                relationship_type=AssetRelationshipType.CONTAINS,
            ),
            AssetRelationship(
                source_asset_key="svc-asteria-editor",
                target_asset_key="svc-orbit-catalog",
                relationship_type=AssetRelationshipType.DEPENDS_ON,
            ),
        ),
        direct_incidents=(
            Incident(
                incident_key="inc-orbit-001",
                primary_affected_asset_key="svc-orbit-catalog",
                severity=IncidentSeverity.HIGH,
                title="Catalog lookup timeouts",
                started_at=datetime(2026, 8, 15, 10, 0, tzinfo=UTC),
                resolved_at=datetime(2026, 8, 15, 12, 0, tzinfo=UTC),
            ),
        ),
    )


def test_adapter_projects_existing_dependency_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    context = _dependency_context()
    calls: list[tuple[Session, UUID]] = []

    def load_candidate_dependency_context(
        received_session: Session,
        candidate_id: UUID,
    ) -> CandidateDependencyContext:
        calls.append((received_session, candidate_id))
        return context

    monkeypatch.setattr(
        reader_module,
        "load_candidate_dependency_context",
        load_candidate_dependency_context,
    )
    reader = DatabaseCandidateInvestigationReader(session=session)

    investigation = reader.read_candidate_dependency_context(CANDIDATE_ID)

    assert calls == [(session, CANDIDATE_ID)]
    assert investigation is not None
    assert investigation.candidate_id == CANDIDATE_ID
    assert investigation.candidate_asset.asset_key == "app-asteria-canvas"
    assert investigation.candidate_asset.asset_type is AssetType.APPLICATION
    assert tuple(item.asset_key for item in investigation.dependency_anchors) == (
        "svc-asteria-editor",
        "svc-orbit-catalog",
    )
    assert tuple(item.asset_key for item in investigation.direct_dependencies) == (
        "svc-orbit-catalog",
    )
    assert tuple(item.asset_key for item in investigation.direct_dependents) == (
        "svc-asteria-editor",
        "svc-borealis-renderer",
    )
    assert tuple(item.asset_key for item in investigation.reachable_dependents) == (
        "svc-borealis-renderer",
    )
    assert not hasattr(investigation, "impact")
    assert not hasattr(investigation, "causality")


def test_adapter_projects_existing_enterprise_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    context = _enterprise_context()
    calls: list[tuple[Session, UUID]] = []

    def load_candidate_enterprise_context(
        received_session: Session,
        candidate_id: UUID,
    ) -> CandidateEnterpriseContext:
        calls.append((received_session, candidate_id))
        return context

    monkeypatch.setattr(
        reader_module,
        "load_candidate_enterprise_context",
        load_candidate_enterprise_context,
    )
    reader = DatabaseCandidateInvestigationReader(session=session)

    investigation = reader.read_candidate_enterprise_context(CANDIDATE_ID)

    assert calls == [(session, CANDIDATE_ID)]
    assert investigation is not None
    assert investigation.candidate_id == CANDIDATE_ID
    assert investigation.enterprise_asset.asset_key == "svc-orbit-catalog"
    assert investigation.enterprise_asset.criticality is AssetCriticality.HIGH
    assert investigation.enterprise_ownerships[0].asset_ownership.team_key == (
        "team-orbit"
    )
    assert investigation.enterprise_ownerships[0].team.name == "Orbit Platform Team"
    assert investigation.direct_relationships[0].relationship_type is (
        AssetRelationshipType.CONTAINS
    )
    assert investigation.direct_incidents[0].incident_key == "inc-orbit-001"
    assert investigation.direct_incidents[0].severity is IncidentSeverity.HIGH
    assert not hasattr(investigation, "risk")
    assert not hasattr(investigation, "validated_ownership")
    assert not hasattr(investigation.direct_incidents[0], "candidate_risk")


def test_adapter_preserves_unknown_candidate_for_context_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = cast(Session, object())
    monkeypatch.setattr(
        reader_module,
        "load_candidate_dependency_context",
        lambda _session, _candidate_id: None,
    )
    monkeypatch.setattr(
        reader_module,
        "load_candidate_enterprise_context",
        lambda _session, _candidate_id: None,
    )
    reader = DatabaseCandidateInvestigationReader(session)

    assert reader.read_candidate_dependency_context(CANDIDATE_ID) is None
    assert reader.read_candidate_enterprise_context(CANDIDATE_ID) is None
