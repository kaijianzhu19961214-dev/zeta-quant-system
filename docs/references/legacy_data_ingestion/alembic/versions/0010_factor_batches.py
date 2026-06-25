"""factor and qfq batch tables

Revision ID: 0010_factor_batches
Revises: 0009_qfq_base_date
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0010_factor_batches"
down_revision: str | None = "0009_qfq_base_date"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adjustment_factors",
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("adj_factor", sa.Numeric(24, 10), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("dataset_code", "code", "date"),
    )
    op.create_index(
        "ix_adjustment_factors_code_date",
        "adjustment_factors",
        ["code", "date"],
    )
    op.create_index(
        "ix_adjustment_factors_dataset_date",
        "adjustment_factors",
        ["dataset_code", "date"],
    )

    op.create_table(
        "qfq_batches",
        sa.Column("batch_id", sa.String(length=64), nullable=False),
        sa.Column("qfq_base_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("batch_id"),
    )
    op.create_index("ix_qfq_batches_base_date", "qfq_batches", ["qfq_base_date"])
    op.create_index("ix_qfq_batches_status", "qfq_batches", ["status"])


def downgrade() -> None:
    op.drop_index("ix_qfq_batches_status", table_name="qfq_batches")
    op.drop_index("ix_qfq_batches_base_date", table_name="qfq_batches")
    op.drop_table("qfq_batches")

    op.drop_index("ix_adjustment_factors_dataset_date", table_name="adjustment_factors")
    op.drop_index("ix_adjustment_factors_code_date", table_name="adjustment_factors")
    op.drop_table("adjustment_factors")
