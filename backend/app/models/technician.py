from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer


class Technician(OrganizationScopedMixin, Base):
    __tablename__ = "technicians"

    technician_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    role: Mapped[Optional[str]] = mapped_column(
        String(50), server_default="ET Technician"
    )
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="technician")
