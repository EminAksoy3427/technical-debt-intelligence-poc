from dataclasses import dataclass

from app.domain.enterprise_estate import AssetType


@dataclass(frozen=True)
class CanonicalAssetRef:
    asset_key: str
    asset_type: AssetType

    def __post_init__(self) -> None:
        if not self.asset_key.strip():
            raise ValueError("Canonical asset key must not be blank")
        if not isinstance(self.asset_type, AssetType):
            raise ValueError("Canonical asset type must be supported")
