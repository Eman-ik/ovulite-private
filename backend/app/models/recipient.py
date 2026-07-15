from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer


class Recipient(OrganizationScopedMixin, Base):
    __tablename__ = "recipients"

    recipient_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    tag_id: Mapped[str] = mapped_column(String(50), nullable=False)
    farm_location: Mapped[Optional[str]] = mapped_column(String(200))
    cow_or_heifer: Mapped[Optional[str]] = mapped_column(String(20))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    transfers: Mapped[list["ETTransfer"]] = relationship(back_populates="recipient")

    __table_args__ = (
        CheckConstraint(
            "cow_or_heifer IN ('Cow', 'Heifer')",
            name="ck_recipients_cow_or_heifer",
        ),
    )
