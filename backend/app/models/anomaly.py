from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.mixins import OrganizationScopedMixin


class Anomaly(OrganizationScopedMixin, Base):
    __tablename__ = "anomalies"

    anomaly_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    anomaly_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_type: Mapped[Optional[str]] = mapped_column(String(50))
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[Optional[str]] = mapped_column(String(20))
    description: Mapped[Optional[str]] = mapped_column(Text)
    metric_value: Mapped[Optional[Decimal]] = mapped_column()
    baseline_value: Mapped[Optional[Decimal]] = mapped_column()
    detected_at: Mapped[datetime] = mapped_column(server_default=func.now())
