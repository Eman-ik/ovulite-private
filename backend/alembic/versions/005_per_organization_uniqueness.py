"""Make tag_id/name uniqueness per-organization instead of global.

donors.tag_id, technicians.name, and protocols.name were declared globally
unique (a leftover from before multi-tenancy was added), which means two
different organizations can never both have e.g. a donor tagged "D1" or a
protocol named "CIDR+GnRH+PGF+GnRH" — even though they have no relationship
to each other. Replace each global UNIQUE with a composite
UNIQUE(organization_id, <column>).

Revision ID: 005_per_org_uniqueness
Revises: 004_token_revocation
"""

import sqlalchemy as sa
from alembic import op

revision = "005_per_org_uniqueness"
down_revision = "004_token_revocation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("donors_tag_id_key", "donors", type_="unique")
    op.create_unique_constraint(
        "uq_donors_org_tag_id", "donors", ["organization_id", "tag_id"]
    )

    op.drop_constraint("technicians_name_key", "technicians", type_="unique")
    op.create_unique_constraint(
        "uq_technicians_org_name", "technicians", ["organization_id", "name"]
    )

    op.drop_constraint("protocols_name_key", "protocols", type_="unique")
    op.create_unique_constraint(
        "uq_protocols_org_name", "protocols", ["organization_id", "name"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_protocols_org_name", "protocols", type_="unique")
    op.create_unique_constraint("protocols_name_key", "protocols", ["name"])

    op.drop_constraint("uq_technicians_org_name", "technicians", type_="unique")
    op.create_unique_constraint("technicians_name_key", "technicians", ["name"])

    op.drop_constraint("uq_donors_org_tag_id", "donors", type_="unique")
    op.create_unique_constraint("donors_tag_id_key", "donors", ["tag_id"])
