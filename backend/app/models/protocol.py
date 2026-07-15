from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer
    from app.models.protocol_log import ProtocolLog


class Protocol(OrganizationScopedMixin, Base):
    __tablename__ = "protocols"

    protocol_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="protocol")
    protocol_logs: Mapped[list["ProtocolLog"]] = relationship(
        back_populates="protocol"
    )
