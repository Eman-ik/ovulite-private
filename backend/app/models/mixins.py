from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class OrganizationScopedMixin:
    """Mixin for rows that belong to a single organization."""

    organization_id: Mapped[int] = mapped_column(
        ForeignKey("organizations.organization_id"),
        nullable=False,
        index=True,
    )
