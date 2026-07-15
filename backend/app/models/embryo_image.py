from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo


class EmbryoImage(OrganizationScopedMixin, Base):
    __tablename__ = "embryo_images"

    image_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    embryo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("embryos.embryo_id")
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_hash: Mapped[Optional[str]] = mapped_column(String(64))
    width_px: Mapped[Optional[int]] = mapped_column(Integer)
    height_px: Mapped[Optional[int]] = mapped_column(Integer)
    uploaded_at: Mapped[datetime] = mapped_column(server_default=func.now())
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Relationships
    embryo: Mapped[Optional["Embryo"]] = relationship(back_populates="images")
