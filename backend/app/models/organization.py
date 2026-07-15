from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.user import User


class Organization(Base):
    __tablename__ = "organizations"

    organization_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    organization_type: Mapped[Optional[str]] = mapped_column(String(80))
    country: Mapped[Optional[str]] = mapped_column(String(80))
    time_zone: Mapped[Optional[str]] = mapped_column(String(80))
    primary_species: Mapped[Optional[str]] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    memberships = relationship("OrganizationMembership", back_populates="organization")
    invitations = relationship("OrganizationInvitation", back_populates="organization")
    users = relationship("User", back_populates="organization")


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"

    membership_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), server_default="active")
    is_primary: Mapped[bool] = mapped_column(Boolean, server_default="false")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    organization = relationship("Organization", back_populates="memberships")
    user = relationship("User", back_populates="memberships")

    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", name="uq_org_memberships_user"),
    )


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    invitation_id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.organization_id"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    invited_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.user_id"), nullable=False
    )
    token: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(20), server_default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    organization = relationship("Organization", back_populates="invitations")
