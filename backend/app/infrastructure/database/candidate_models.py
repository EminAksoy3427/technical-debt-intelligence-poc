from uuid import UUID

from sqlalchemy import ForeignKey, Unicode, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base
from app.infrastructure.database.enterprise_estate_models import EnterpriseAssetModel
from app.infrastructure.database.signal_models import SignalModel


class CandidateModel(Base):
    __tablename__ = "candidates"

    candidate_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    canonical_asset_id: Mapped[int] = mapped_column(
        ForeignKey(
            "enterprise_assets.id",
            name="fk_candidates_canonical_asset_id_enterprise_assets",
        ),
        nullable=False,
    )
    hypothesis: Mapped[str] = mapped_column(Unicode(1000), nullable=False)
    correlation_rationale: Mapped[str] = mapped_column(Unicode(2000), nullable=False)

    canonical_asset: Mapped[EnterpriseAssetModel] = relationship()
    signal_memberships: Mapped[list["CandidateSignalModel"]] = relationship(
        back_populates="candidate",
        cascade="all, delete-orphan",
    )


class CandidateSignalModel(Base):
    __tablename__ = "candidate_signals"

    candidate_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "candidates.candidate_id",
            name="fk_candidate_signals_candidate_id_candidates",
        ),
        primary_key=True,
    )
    signal_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "signals.signal_id",
            name="fk_candidate_signals_signal_id_signals",
        ),
        primary_key=True,
    )

    candidate: Mapped[CandidateModel] = relationship(
        back_populates="signal_memberships"
    )
    signal: Mapped[SignalModel] = relationship()
