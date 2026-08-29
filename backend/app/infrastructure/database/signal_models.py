from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Unicode, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel


class SignalModel(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint(
            "source_system",
            "source_record_id",
            name="uq_signals_source_system_source_record_id",
        ),
    )

    signal_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    source_system: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    source_record_id: Mapped[str] = mapped_column(Unicode(500), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    affected_asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_signals_affected_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    severity: Mapped[str | None] = mapped_column(Unicode(32), nullable=True)

    affected_asset: Mapped[EnterpriseAssetModel] = relationship()
    evidence: Mapped[list["EvidenceModel"]] = relationship(back_populates="signal")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    evidence_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey("signals.signal_id", name="fk_evidence_signal_id_signals"),
        nullable=False,
    )
    source_system: Mapped[str] = mapped_column(Unicode(100), nullable=False)
    source_reference: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    reference_uri: Mapped[str | None] = mapped_column(Unicode(2048), nullable=True)

    signal: Mapped[SignalModel] = relationship(back_populates="evidence")
