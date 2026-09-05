"""Add OPU Session and IVF Batch as first-class entities.

Ovulite's intended reproductive lineage is Donor -> OPU Session -> IVF Batch
-> Embryo -> Recipient -> ET -> Outcome. Until now, OPU was just a flat
`opu_date` column on Embryo and there was no IVF Batch table at all, so
there was nowhere to record OPU-level counts (follicles/oocytes recovered)
or IVF-batch-level counts (cleavage/blastocyst rates).

This migration adds both tables and backfills the existing embryo records:
- opu_sessions are grouped from embryos by (organization_id, donor_id, opu_date)
- ivf_batches are grouped from the resulting opu_id by (organization_id, opu_id, sire_id)

Embryos with no opu_date (69 of 489 at the time this was written) are left
unlinked (opu_id/ivf_batch_id NULL) rather than grouped into a fabricated
session — the flat historical data doesn't support inferring one safely.

Revision ID: 006_opu_ivf_batch
Revises: 005_per_org_uniqueness
"""

import sqlalchemy as sa
from alembic import op

revision = "006_opu_ivf_batch"
down_revision = "005_per_org_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "opu_sessions",
        sa.Column("opu_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("donor_id", sa.Integer(), sa.ForeignKey("donors.donor_id"), nullable=False),
        sa.Column("opu_date", sa.Date(), nullable=False),
        sa.Column("technician_id", sa.Integer(), sa.ForeignKey("technicians.technician_id")),
        sa.Column("farm_location", sa.String(200)),
        sa.Column("total_follicles", sa.Integer()),
        sa.Column("oocytes_recovered", sa.Integer()),
        sa.Column("viable_oocytes", sa.Integer()),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_opu_sessions_organization_id", "opu_sessions", ["organization_id"])
    op.create_index("ix_opu_sessions_donor_id", "opu_sessions", ["donor_id"])

    op.create_table(
        "ivf_batches",
        sa.Column("ivf_batch_id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("organization_id", sa.Integer(), sa.ForeignKey("organizations.organization_id"), nullable=False),
        sa.Column("opu_id", sa.Integer(), sa.ForeignKey("opu_sessions.opu_id"), nullable=False),
        sa.Column("sire_id", sa.Integer(), sa.ForeignKey("sires.sire_id")),
        sa.Column("ivf_date", sa.Date()),
        sa.Column("oocytes_used", sa.Integer()),
        sa.Column("mature_oocytes", sa.Integer()),
        sa.Column("cleaved_embryos", sa.Integer()),
        sa.Column("blastocysts", sa.Integer()),
        sa.Column("degenerated_embryos", sa.Integer()),
        sa.Column("culture_media", sa.String(100)),
        sa.Column("embryologist_id", sa.Integer(), sa.ForeignKey("technicians.technician_id")),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )
    op.create_index("ix_ivf_batches_organization_id", "ivf_batches", ["organization_id"])
    op.create_index("ix_ivf_batches_opu_id", "ivf_batches", ["opu_id"])

    op.add_column("embryos", sa.Column("opu_id", sa.Integer(), sa.ForeignKey("opu_sessions.opu_id"), nullable=True))
    op.add_column("embryos", sa.Column("ivf_batch_id", sa.Integer(), sa.ForeignKey("ivf_batches.ivf_batch_id"), nullable=True))

    bind = op.get_bind()

    # Backfill opu_sessions from historical embryo (donor_id, opu_date) groups.
    bind.execute(sa.text("""
        INSERT INTO opu_sessions (organization_id, donor_id, opu_date, notes)
        SELECT DISTINCT organization_id, donor_id, opu_date,
               'Backfilled from historical embryo records (migration 006)'
        FROM embryos
        WHERE donor_id IS NOT NULL AND opu_date IS NOT NULL
    """))

    bind.execute(sa.text("""
        UPDATE embryos e
        SET opu_id = o.opu_id
        FROM opu_sessions o
        WHERE e.organization_id = o.organization_id
          AND e.donor_id = o.donor_id
          AND e.opu_date = o.opu_date
    """))

    # Backfill ivf_batches from the resulting (opu_id, sire_id) groups.
    bind.execute(sa.text("""
        INSERT INTO ivf_batches (organization_id, opu_id, sire_id, notes)
        SELECT DISTINCT organization_id, opu_id, sire_id,
               'Backfilled from historical embryo records (migration 006)'
        FROM embryos
        WHERE opu_id IS NOT NULL
    """))

    bind.execute(sa.text("""
        UPDATE embryos e
        SET ivf_batch_id = b.ivf_batch_id
        FROM ivf_batches b
        WHERE e.organization_id = b.organization_id
          AND e.opu_id = b.opu_id
          AND (e.sire_id = b.sire_id OR (e.sire_id IS NULL AND b.sire_id IS NULL))
    """))


def downgrade() -> None:
    op.drop_column("embryos", "ivf_batch_id")
    op.drop_column("embryos", "opu_id")
    op.drop_index("ix_ivf_batches_opu_id", table_name="ivf_batches")
    op.drop_index("ix_ivf_batches_organization_id", table_name="ivf_batches")
    op.drop_table("ivf_batches")
    op.drop_index("ix_opu_sessions_donor_id", table_name="opu_sessions")
    op.drop_index("ix_opu_sessions_organization_id", table_name="opu_sessions")
    op.drop_table("opu_sessions")
