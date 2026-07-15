from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo


class Sire(OrganizationScopedMixin, Base):
    __tablename__ = "sires"

    sire_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    breed: Mapped[Optional[str]] = mapped_column(String(100))
    birth_weight_epd: Mapped[Optional[Decimal]] = mapped_column()
    semen_type: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    embryos: Mapped[list["Embryo"]] = relationship(back_populates="sire")

    __table_args__ = (
        CheckConstraint(
            "semen_type IN ('Conventional', 'Sexed', 'Unknown')",
            name="ck_sires_semen_type",
        ),
    )
