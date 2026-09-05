from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.donor import Donor
    from app.models.embryo_image import EmbryoImage
    from app.models.et_transfer import ETTransfer
    from app.models.ivf_batch import IVFBatch
    from app.models.opu_session import OPUSession
    from app.models.sire import Sire


class Embryo(OrganizationScopedMixin, Base):
    __tablename__ = "embryos"

    embryo_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    donor_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("donors.donor_id")
    )
    sire_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("sires.sire_id")
    )
    opu_id: Mapped[Optional[int]] = mapped_column(ForeignKey("opu_sessions.opu_id"))
    ivf_batch_id: Mapped[Optional[int]] = mapped_column(ForeignKey("ivf_batches.ivf_batch_id"))
    opu_date: Mapped[Optional[date]] = mapped_column(Date)
    stage: Mapped[Optional[int]] = mapped_column(Integer)
    grade: Mapped[Optional[int]] = mapped_column(Integer)
    fresh_or_frozen: Mapped[Optional[str]] = mapped_column(String(20))
    cane_number: Mapped[Optional[str]] = mapped_column(String(50))
    freezing_date: Mapped[Optional[date]] = mapped_column(Date)
    ai_grade: Mapped[Optional[int]] = mapped_column(Integer)
    ai_viability: Mapped[Optional[Decimal]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    donor: Mapped[Optional["Donor"]] = relationship(back_populates="embryos")
    sire: Mapped[Optional["Sire"]] = relationship(back_populates="embryos")
    opu_session: Mapped[Optional["OPUSession"]] = relationship(back_populates="embryos")
    ivf_batch: Mapped[Optional["IVFBatch"]] = relationship(back_populates="embryos")
    images: Mapped[list["EmbryoImage"]] = relationship(back_populates="embryo")
    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="embryo")

    __table_args__ = (
        CheckConstraint("stage BETWEEN 1 AND 9", name="ck_embryos_stage"),
        CheckConstraint("grade BETWEEN 1 AND 4", name="ck_embryos_grade"),
        CheckConstraint(
            "fresh_or_frozen IN ('Fresh', 'Frozen')",
            name="ck_embryos_fresh_or_frozen",
        ),
    )
