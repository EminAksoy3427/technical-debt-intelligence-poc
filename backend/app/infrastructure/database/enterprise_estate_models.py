from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Integer,
    Unicode,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base


class EnterpriseAssetModel(Base):
    __tablename__ = "enterprise_assets"
    __table_args__ = (
        CheckConstraint(
            "asset_type IN ('APPLICATION', 'SERVICE', 'REPOSITORY')",
            name="ck_enterprise_assets_asset_type",
        ),
        CheckConstraint(
            "criticality IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_enterprise_assets_criticality",
        ),
        CheckConstraint(
            "lifecycle_status IN ('PLANNED', 'ACTIVE', 'RETIRED')",
            name="ck_enterprise_assets_lifecycle_status",
        ),
        UniqueConstraint("asset_key", name="uq_enterprise_assets_asset_key"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    asset_key: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    asset_type: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)
    criticality: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    lifecycle_status: Mapped[str] = mapped_column(Unicode(32), nullable=False)

    ownerships: Mapped[list["AssetOwnershipModel"]] = relationship(
        back_populates="asset"
    )
    outgoing_relationships: Mapped[list["AssetRelationshipModel"]] = relationship(
        foreign_keys="AssetRelationshipModel.source_asset_id",
        back_populates="source_asset",
    )
    incoming_relationships: Mapped[list["AssetRelationshipModel"]] = relationship(
        foreign_keys="AssetRelationshipModel.target_asset_id",
        back_populates="target_asset",
    )
    incidents: Mapped[list["IncidentModel"]] = relationship(
        back_populates="primary_affected_asset"
    )


class TeamModel(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("team_key", name="uq_teams_team_key"),)

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    team_key: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    name: Mapped[str] = mapped_column(Unicode(200), nullable=False)

    ownerships: Mapped[list["AssetOwnershipModel"]] = relationship(
        back_populates="team"
    )


class AssetOwnershipModel(Base):
    __tablename__ = "asset_ownerships"
    __table_args__ = (
        CheckConstraint(
            "ownership_role IN ('PRIMARY', 'SUPPORTING')",
            name="ck_asset_ownerships_role",
        ),
        UniqueConstraint(
            "asset_id",
            "team_id",
            "ownership_role",
            name="uq_asset_ownerships_asset_team_role",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_asset_ownerships_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", name="fk_asset_ownerships_team_id_teams"),
        nullable=False,
    )
    ownership_role: Mapped[str] = mapped_column(Unicode(32), nullable=False)

    asset: Mapped[EnterpriseAssetModel] = relationship(back_populates="ownerships")
    team: Mapped[TeamModel] = relationship(back_populates="ownerships")


class AssetRelationshipModel(Base):
    __tablename__ = "asset_relationships"
    __table_args__ = (
        CheckConstraint(
            "relationship_type IN ('CONTAINS', 'IMPLEMENTED_BY', 'DEPENDS_ON')",
            name="ck_asset_relationships_type",
        ),
        UniqueConstraint(
            "source_asset_id",
            "target_asset_id",
            "relationship_type",
            name="uq_asset_relationships_edge",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    source_asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_asset_relationships_source_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    target_asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_asset_relationships_target_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(Unicode(32), nullable=False)

    source_asset: Mapped[EnterpriseAssetModel] = relationship(
        foreign_keys=[source_asset_id],
        back_populates="outgoing_relationships",
    )
    target_asset: Mapped[EnterpriseAssetModel] = relationship(
        foreign_keys=[target_asset_id],
        back_populates="incoming_relationships",
    )


class IncidentModel(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')",
            name="ck_incidents_severity",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= started_at",
            name="ck_incidents_resolution_not_before_start",
        ),
        UniqueConstraint("incident_key", name="uq_incidents_incident_key"),
    )

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    incident_key: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    primary_affected_asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_incidents_primary_affected_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    severity: Mapped[str] = mapped_column(Unicode(32), nullable=False)
    title: Mapped[str] = mapped_column(Unicode(300), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    primary_affected_asset: Mapped[EnterpriseAssetModel] = relationship(
        back_populates="incidents"
    )
