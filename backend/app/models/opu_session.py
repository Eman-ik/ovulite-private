from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.donor import Donor
    from app.models.embryo import Embryo
    from app.models.ivf_batch import IVFBatch
    from app.models.technician import Technician


class OPUSession(OrganizationScopedMixin, Base):
    """A single ovum-pickup event for one donor.

    Backfilled rows (see migration 006) are grouped from historical embryo
    records by (donor_id, opu_date) — the only grouping the flat historical
    data actually supports. Follicle/oocyte counts are unknown for those and
    left null rather than fabricated.
    """

    __tablename__ = "opu_sessions"

    opu_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    donor_id: Mapped[int] = mapped_column(ForeignKey("donors.donor_id"), nullable=False)
    opu_date: Mapped[date] = mapped_column(Date, nullable=False)
    technician_id: Mapped[Optional[int]] = mapped_column(ForeignKey("technicians.technician_id"))
    farm_location: Mapped[Optional[str]] = mapped_column(String(200))
    total_follicles: Mapped[Optional[int]] = mapped_column(Integer)
    oocytes_recovered: Mapped[Optional[int]] = mapped_column(Integer)
    viable_oocytes: Mapped[Optional[int]] = mapped_column(Integer)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())

    donor: Mapped["Donor"] = relationship(back_populates="opu_sessions")
    technician: Mapped[Optional["Technician"]] = relationship()
    embryos: Mapped[list["Embryo"]] = relationship(back_populates="opu_session")
    ivf_batches: Mapped[list["IVFBatch"]] = relationship(back_populates="opu_session")
