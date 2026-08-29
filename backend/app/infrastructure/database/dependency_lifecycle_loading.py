from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.assets import CanonicalAssetRef
from app.domain.enterprise_estate import AssetType
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.dependency_lifecycle import DependencyLifecycleFinding


def resolve_dependency_lifecycle_affected_asset(
    session: Session,
    finding: DependencyLifecycleFinding,
) -> CanonicalAssetRef:
    """Resolve a lifecycle finding's stable asset key from the enterprise catalog."""
    affected_asset = session.scalar(
        select(EnterpriseAssetModel).where(
            EnterpriseAssetModel.asset_key == finding.affected_asset_key
        )
    )
    if affected_asset is None:
        raise ValueError(
            "Dependency lifecycle affected asset does not exist in the "
            "enterprise catalog"
        )
    return CanonicalAssetRef(
        asset_key=affected_asset.asset_key,
        asset_type=AssetType(affected_asset.asset_type),
    )
