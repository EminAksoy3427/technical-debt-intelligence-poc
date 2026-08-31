from dataclasses import dataclass
from uuid import UUID

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType


def _ordered_unique_services(
    assets: tuple[CanonicalAssetRef, ...],
) -> tuple[CanonicalAssetRef, ...]:
    assets_by_key: dict[str, CanonicalAssetRef] = {}
    for asset in assets:
        if not isinstance(asset, CanonicalAssetRef):
            raise ValueError(
                "Dependency context assets must be canonical asset references"
            )
        if asset.asset_type is not AssetType.SERVICE:
            raise ValueError("Dependency context graph assets must be Services")
        existing = assets_by_key.get(asset.asset_key)
        if existing is not None and existing != asset:
            raise ValueError("Dependency context asset identity must be stable")
        assets_by_key[asset.asset_key] = asset
    return tuple(assets_by_key[key] for key in sorted(assets_by_key))


@dataclass(frozen=True)
class CandidateDependencyContext:
    """Deterministic dependency reachability facts for a Candidate asset."""

    candidate_id: UUID
    candidate_asset: CanonicalAssetRef
    dependency_anchors: tuple[CanonicalAssetRef, ...]
    direct_dependencies: tuple[CanonicalAssetRef, ...]
    direct_dependents: tuple[CanonicalAssetRef, ...]
    reachable_dependents: tuple[CanonicalAssetRef, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_asset, CanonicalAssetRef):
            raise ValueError("Candidate dependency context asset must be canonical")

        for field_name in (
            "dependency_anchors",
            "direct_dependencies",
            "direct_dependents",
            "reachable_dependents",
        ):
            assets = tuple(getattr(self, field_name))
            object.__setattr__(self, field_name, _ordered_unique_services(assets))
