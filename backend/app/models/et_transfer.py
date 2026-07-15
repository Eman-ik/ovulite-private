from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import OrganizationScopedMixin

if TYPE_CHECKING:
    from app.models.embryo import Embryo
    from app.models.prediction import Prediction
    from app.models.protocol import Protocol
    from app.models.protocol_log import ProtocolLog
    from app.models.recipient import Recipient
    from app.models.technician import Technician


class ETTransfer(OrganizationScopedMixin, Base):
    __tablename__ = "et_transfers"

    transfer_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    et_number: Mapped[Optional[int]] = mapped_column(Integer)
    lab: Mapped[Optional[str]] = mapped_column(String(50))
    satellite: Mapped[Optional[str]] = mapped_column(String(50))
    customer_id: Mapped[Optional[str]] = mapped_column(String(50))
    et_date: Mapped[date] = mapped_column(Date, nullable=False)
    farm_location: Mapped[Optional[str]] = mapped_column(String(200))

    # Recipient
    recipient_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("recipients.recipient_id")
    )
    bc_score: Mapped[Optional[Decimal]] = mapped_column()

    # CL (Corpus Luteum) data
    cl_side: Mapped[Optional[str]] = mapped_column(String(10))
    cl_measure_mm: Mapped[Optional[Decimal]] = mapped_column()

    # Synchronization
    protocol_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("protocols.protocol_id")
    )
    heat_observed: Mapped[Optional[bool]] = mapped_column(Boolean)
    heat_day: Mapped[Optional[int]] = mapped_column(Integer)

    # Embryo
    embryo_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("embryos.embryo_id")
    )

    # Staff
    technician_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("technicians.technician_id")
    )
    assistant_name: Mapped[Optional[str]] = mapped_column(String(100))

    # Outcome (POST-TRANSFER — leakage risk!)
    pc1_date: Mapped[Optional[date]] = mapped_column(Date)
    pc1_result: Mapped[Optional[str]] = mapped_column(String(20))
    pc2_date: Mapped[Optional[date]] = mapped_column(Date)
    pc2_result: Mapped[Optional[str]] = mapped_column(String(20))
    fetal_sexing: Mapped[Optional[str]] = mapped_column(String(20))
    days_in_pregnancy: Mapped[Optional[int]] = mapped_column(Integer)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    recipient: Mapped[Optional["Recipient"]] = relationship(
        back_populates="transfers"
    )
    protocol: Mapped[Optional["Protocol"]] = relationship(
        back_populates="transfers"
    )
    embryo: Mapped[Optional["Embryo"]] = relationship(back_populates="transfers")
    technician: Mapped[Optional["Technician"]] = relationship(
        back_populates="transfers"
    )
    predictions: Mapped[list["Prediction"]] = relationship(
        back_populates="transfer"
    )
    protocol_logs: Mapped[list["ProtocolLog"]] = relationship(
        back_populates="transfer"
    )

    __table_args__ = (
        CheckConstraint(
            "pc1_result IN ('Pregnant', 'Open', 'Recheck') OR pc1_result IS NULL",
            name="ck_et_transfers_pc1_result",
        ),
    )
