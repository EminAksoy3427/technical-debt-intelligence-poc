from uuid import UUID

import networkx as nx
from sqlalchemy import select
from sqlalchemy.orm import Session, aliased

from app.domain.assets import CanonicalAssetRef
from app.domain.candidate_dependency_context import CandidateDependencyContext
from app.domain.enterprise_estate import AssetRelationshipType, AssetType
from app.infrastructure.database.candidate_models import CandidateModel
from app.infrastructure.database.enterprise_estate_models import (
    AssetRelationshipModel,
    EnterpriseAssetModel,
)


class CandidateDependencyContextIntegrityError(ValueError):
    """A persisted Candidate cannot be projected onto its canonical asset."""


def load_candidate_dependency_context(
    session: Session,
    candidate_id: UUID,
) -> CandidateDependencyContext | None:
    """Load read-only dependency reachability context for a persisted Candidate."""
    with session.no_autoflush:
        candidate_row = session.execute(
            select(
                CandidateModel.candidate_id,
                CandidateModel.canonical_asset_id,
            ).where(CandidateModel.candidate_id == candidate_id)
        ).one_or_none()
        if candidate_row is None:
            return None
        if candidate_row.canonical_asset_id is None:
            raise CandidateDependencyContextIntegrityError(
                "Candidate canonical enterprise asset identity is missing"
            )

        candidate_asset = _load_candidate_asset(
            session,
            candidate_row.canonical_asset_id,
        )
        dependency_anchors = _resolve_dependency_anchors(
            session,
            candidate_row.canonical_asset_id,
            candidate_asset,
        )
        graph, service_assets = _load_dependency_graph(session)

    direct_dependency_keys: set[str] = set()
    direct_dependent_keys: set[str] = set()
    reachable_dependent_keys: set[str] = set()
    anchor_keys = {anchor.asset_key for anchor in dependency_anchors}

    for anchor in dependency_anchors:
        anchor_key = anchor.asset_key
        direct_dependency_keys.update(
            neighbor
            for neighbor in graph.successors(anchor_key)
            if neighbor != anchor_key
        )
        direct_dependent_keys.update(
            neighbor
            for neighbor in graph.predecessors(anchor_key)
            if neighbor != anchor_key
        )
        reachable_dependent_keys.update(nx.ancestors(graph, anchor_key))

    reachable_dependent_keys.difference_update(anchor_keys)
    return CandidateDependencyContext(
        candidate_id=candidate_id,
        candidate_asset=candidate_asset,
        dependency_anchors=dependency_anchors,
        direct_dependencies=_assets_for_keys(service_assets, direct_dependency_keys),
        direct_dependents=_assets_for_keys(service_assets, direct_dependent_keys),
        reachable_dependents=_assets_for_keys(
            service_assets,
            reachable_dependent_keys,
        ),
    )


def _load_candidate_asset(
    session: Session,
    canonical_asset_id: int,
) -> CanonicalAssetRef:
    row = session.execute(
        select(
            EnterpriseAssetModel.asset_key,
            EnterpriseAssetModel.asset_type,
        ).where(EnterpriseAssetModel.id == canonical_asset_id)
    ).one_or_none()
    if row is None:
        raise CandidateDependencyContextIntegrityError(
            "Candidate canonical enterprise asset is missing"
        )
    try:
        return CanonicalAssetRef(
            asset_key=row.asset_key,
            asset_type=AssetType(row.asset_type),
        )
    except ValueError as error:
        raise CandidateDependencyContextIntegrityError(
            "Candidate canonical enterprise asset is invalid"
        ) from error


def _resolve_dependency_anchors(
    session: Session,
    canonical_asset_id: int,
    candidate_asset: CanonicalAssetRef,
) -> tuple[CanonicalAssetRef, ...]:
    if candidate_asset.asset_type is AssetType.SERVICE:
        return (candidate_asset,)
    if candidate_asset.asset_type is AssetType.REPOSITORY:
        return _load_structural_service_anchors(
            session,
            canonical_asset_id=canonical_asset_id,
            relationship_type=AssetRelationshipType.IMPLEMENTED_BY,
            candidate_is_source=False,
        )
    return _load_structural_service_anchors(
        session,
        canonical_asset_id=canonical_asset_id,
        relationship_type=AssetRelationshipType.CONTAINS,
        candidate_is_source=True,
    )


def _load_structural_service_anchors(
    session: Session,
    *,
    canonical_asset_id: int,
    relationship_type: AssetRelationshipType,
    candidate_is_source: bool,
) -> tuple[CanonicalAssetRef, ...]:
    service_asset = aliased(EnterpriseAssetModel)
    if candidate_is_source:
        asset_join = service_asset.id == AssetRelationshipModel.target_asset_id
        candidate_filter = AssetRelationshipModel.source_asset_id == canonical_asset_id
    else:
        asset_join = service_asset.id == AssetRelationshipModel.source_asset_id
        candidate_filter = AssetRelationshipModel.target_asset_id == canonical_asset_id

    rows = session.execute(
        select(service_asset.asset_key)
        .select_from(AssetRelationshipModel)
        .join(service_asset, asset_join)
        .where(
            candidate_filter,
            AssetRelationshipModel.relationship_type == relationship_type.value,
            service_asset.asset_type == AssetType.SERVICE.value,
        )
    )
    return tuple(
        CanonicalAssetRef(asset_key=asset_key, asset_type=AssetType.SERVICE)
        for asset_key in sorted(set(rows.scalars()))
    )


def _load_dependency_graph(
    session: Session,
) -> tuple[nx.DiGraph, dict[str, CanonicalAssetRef]]:
    service_rows = session.execute(
        select(
            EnterpriseAssetModel.id,
            EnterpriseAssetModel.asset_key,
        ).where(EnterpriseAssetModel.asset_type == AssetType.SERVICE.value)
    )
    services_by_id = {
        row.id: CanonicalAssetRef(
            asset_key=row.asset_key,
            asset_type=AssetType.SERVICE,
        )
        for row in service_rows
    }
    services_by_key = {asset.asset_key: asset for asset in services_by_id.values()}

    graph = nx.DiGraph()
    graph.add_nodes_from(sorted(services_by_key))
    dependency_rows = session.execute(
        select(
            AssetRelationshipModel.source_asset_id,
            AssetRelationshipModel.target_asset_id,
        ).where(
            AssetRelationshipModel.relationship_type
            == AssetRelationshipType.DEPENDS_ON.value
        )
    )
    graph.add_edges_from(
        sorted(
            (
                services_by_id[row.source_asset_id].asset_key,
                services_by_id[row.target_asset_id].asset_key,
            )
            for row in dependency_rows
            if row.source_asset_id in services_by_id
            and row.target_asset_id in services_by_id
        )
    )
    return graph, services_by_key


def _assets_for_keys(
    service_assets: dict[str, CanonicalAssetRef],
    asset_keys: set[str],
) -> tuple[CanonicalAssetRef, ...]:
    return tuple(service_assets[asset_key] for asset_key in sorted(asset_keys))
