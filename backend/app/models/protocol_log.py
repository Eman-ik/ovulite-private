from datetime import date, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer
    from app.models.protocol import Protocol


class ProtocolLog(OrganizationScopedMixin, Base):
    __tablename__ = "protocol_logs"

    log_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("et_transfers.transfer_id")
    )
    protocol_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("protocols.protocol_id")
    )
    step_name: Mapped[Optional[str]] = mapped_column(String(100))
    step_date: Mapped[Optional[date]] = mapped_column(Date)
    drug_name: Mapped[Optional[str]] = mapped_column(String(100))
    dosage: Mapped[Optional[str]] = mapped_column(String(50))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    transfer: Mapped[Optional["ETTransfer"]] = relationship(
        back_populates="protocol_logs"
    )
    protocol: Mapped[Optional["Protocol"]] = relationship(
        back_populates="protocol_logs"
    )
