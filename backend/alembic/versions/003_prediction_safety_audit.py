"""Prediction safety and audit fields.

Revision ID: 003_prediction_safety_audit
Revises: 002_organization_tenant_foundation
"""

import sqlalchemy as sa
from alembic import op

revision = "003_prediction_safety_audit"
down_revision = "002_organization_tenant_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fields = [
        sa.Column("feature_snapshot", sa.JSON()),
        sa.Column("feature_schema_version", sa.String(50)),
        sa.Column("request_id", sa.String(50)),
        sa.Column("uncertainty_level", sa.String(20)),
        sa.Column("is_ood", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ood_reasons", sa.JSON()),
        sa.Column("similar_cases", sa.JSON()),
        sa.Column("plain_language_summary", sa.Text()),
        sa.Column("selected_for_case", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("actual_outcome", sa.String(20)),
        sa.Column("actual_outcome_recorded_at", sa.DateTime()),
    ]
    for field in fields:
        op.add_column("predictions", field)
    op.create_index("ix_predictions_request_id", "predictions", ["request_id"], unique=True)
    op.create_check_constraint("ck_predictions_actual_outcome", "predictions", "actual_outcome IN ('Pregnant', 'Open') OR actual_outcome IS NULL")


def downgrade() -> None:
    op.drop_constraint("ck_predictions_actual_outcome", "predictions", type_="check")
    op.drop_index("ix_predictions_request_id", table_name="predictions")
    for name in ["actual_outcome_recorded_at", "actual_outcome", "selected_for_case", "plain_language_summary", "similar_cases", "ood_reasons", "is_ood", "uncertainty_level", "request_id", "feature_schema_version", "feature_snapshot"]:
        op.drop_column("predictions", name)
