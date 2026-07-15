from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import Boolean, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.et_transfer import ETTransfer


class Prediction(OrganizationScopedMixin, Base):
    __tablename__ = "predictions"

    prediction_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    transfer_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("et_transfers.transfer_id")
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_version: Mapped[Optional[str]] = mapped_column(String(50))
    probability: Mapped[Decimal] = mapped_column(nullable=False)
    confidence_lower: Mapped[Optional[Decimal]] = mapped_column()
    confidence_upper: Mapped[Optional[Decimal]] = mapped_column()
    risk_band: Mapped[Optional[str]] = mapped_column(String(20))
    shap_json: Mapped[Optional[Any]] = mapped_column(JSON)
    feature_snapshot: Mapped[Optional[Any]] = mapped_column(JSON)
    feature_schema_version: Mapped[Optional[str]] = mapped_column(String(50))
    request_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    uncertainty_level: Mapped[Optional[str]] = mapped_column(String(20))
    is_ood: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ood_reasons: Mapped[Optional[Any]] = mapped_column(JSON)
    similar_cases: Mapped[Optional[Any]] = mapped_column(JSON)
    plain_language_summary: Mapped[Optional[str]] = mapped_column(Text)
    selected_for_case: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    actual_outcome: Mapped[Optional[str]] = mapped_column(String(20))
    actual_outcome_recorded_at: Mapped[Optional[datetime]] = mapped_column()
    predicted_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Relationships
    transfer: Mapped[Optional["ETTransfer"]] = relationship(
        back_populates="predictions"
    )
