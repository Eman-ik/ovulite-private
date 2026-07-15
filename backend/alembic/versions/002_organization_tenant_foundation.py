"""Organization tenant foundation.

Revision ID: 002_organization_tenant_foundation
Revises: 001_initial_schema
Create Date: 2026-07-11
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_organization_tenant_foundation"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ORG_TABLES = [
    "users",
    "donors",
    "sires",
    "recipients",
    "technicians",
    "protocols",
    "embryos",
    "et_transfers",
    "embryo_images",
    "protocol_logs",
    "predictions",
    "anomalies",
]


def _add_org_column(table_name: str, org_id: int) -> None:
    bind = op.get_bind()
    op.add_column(
        table_name,
        sa.Column("organization_id", sa.Integer(), nullable=True),
    )
    bind.execute(
        sa.text(f"UPDATE {table_name} SET organization_id = :org_id WHERE organization_id IS NULL"),
        {"org_id": org_id},
    )
    op.create_foreign_key(
        f"fk_{table_name}_organization_id_organizations",
        table_name,
        "organizations",
        ["organization_id"],
        ["organization_id"],
    )
    op.alter_column(table_name, "organization_id", nullable=False)
    op.create_index(f"ix_{table_name}_organization_id", table_name, ["organization_id"])


def _drop_org_column(table_name: str) -> None:
    op.drop_index(f"ix_{table_name}_organization_id", table_name=table_name)
    op.drop_constraint(
        f"fk_{table_name}_organization_id_organizations",
        table_name,
        type_="foreignkey",
    )
    op.drop_column(table_name, "organization_id")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("organization_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("slug", sa.String(120), nullable=False, unique=True),
        sa.Column("organization_type", sa.String(80)),
        sa.Column("country", sa.String(80)),
        sa.Column("time_zone", sa.String(80)),
        sa.Column("primary_species", sa.String(80)),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            INSERT INTO organizations (name, slug, organization_type, country, time_zone, primary_species, active)
            VALUES (:name, :slug, :organization_type, :country, :time_zone, :primary_species, :active)
            RETURNING organization_id
            """
        ),
        {
            "name": "Ovulite Default Organization",
            "slug": "ovulite-default",
            "organization_type": "lab",
            "country": "PK",
            "time_zone": "Asia/Karachi",
            "primary_species": "Cattle",
            "active": True,
        },
    )
    org_id = result.scalar_one()

    op.create_table(
        "organization_memberships",
        sa.Column("membership_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=False,
        ),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'active'")),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_memberships_user"),
    )

    op.create_table(
        "organization_invitations",
        sa.Column("invitation_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organizations.organization_id"),
            nullable=False,
        ),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),
        sa.Column("invited_by_user_id", sa.Integer(), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True)),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Update existing user rows to the default organization.
    op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
    bind.execute(
        sa.text("UPDATE users SET organization_id = :org_id WHERE organization_id IS NULL"),
        {"org_id": org_id},
    )
    op.create_foreign_key(
        "fk_users_organization_id_organizations",
        "users",
        "organizations",
        ["organization_id"],
        ["organization_id"],
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('admin', 'veterinarian', 'embryologist', 'viewer', 'et team', 'organization_admin')",
        )
    op.alter_column("users", "organization_id", nullable=False)
    op.create_index("ix_users_organization_id", "users", ["organization_id"])

    for table_name in ORG_TABLES[1:]:
        _add_org_column(table_name, org_id)


def downgrade() -> None:
    for table_name in reversed(ORG_TABLES[1:]):
        _drop_org_column(table_name)

    op.drop_index("ix_users_organization_id", table_name="users")
    op.drop_constraint("fk_users_organization_id_organizations", "users", type_="foreignkey")
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('admin', 'veterinarian', 'embryologist', 'viewer', 'et team')",
        )
    op.drop_column("users", "organization_id")

    op.drop_table("organization_invitations")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
