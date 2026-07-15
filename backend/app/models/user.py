from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("organizations.organization_id")
    )
    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[Optional[str]] = mapped_column(String(50))
    full_name: Mapped[Optional[str]] = mapped_column(String(200))
    email: Mapped[Optional[str]] = mapped_column(String(200))
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    last_login: Mapped[Optional[datetime]] = mapped_column()
    organization = relationship("Organization", back_populates="users")
    memberships = relationship("OrganizationMembership", back_populates="user")

    __table_args__ = (
        CheckConstraint(
            "role IN ('admin', 'veterinarian', 'embryologist', 'viewer', 'et team', 'organization_admin')",
            name="ck_users_role",
        ),
    )
