from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo


class Donor(OrganizationScopedMixin, Base):
    __tablename__ = "donors"

    donor_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    breed: Mapped[Optional[str]] = mapped_column(String(100))
    birth_weight_epd: Mapped[Optional[Decimal]] = mapped_column()
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    embryos: Mapped[list["Embryo"]] = relationship(back_populates="donor")
