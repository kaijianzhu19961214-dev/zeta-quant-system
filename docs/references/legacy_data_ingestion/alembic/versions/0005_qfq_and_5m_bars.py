"""qfq adjustment base and 5m bars

Revision ID: 0005_qfq_5m
Revises: 0004_min_adj
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_qfq_5m"
down_revision: str | None = "0004_min_adj"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    for table_name in ("market_data_1m", "staging_market_data_1m", "market_data_1d"):
        op.add_column(table_name, sa.Column("adjustment_base_factor", sa.Numeric(20, 6), nullable=True))

    op.create_table(
        "market_data_5m",
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=True),
        sa.Column("high", sa.Numeric(20, 6), nullable=True),
        sa.Column("low", sa.Numeric(20, 6), nullable=True),
        sa.Column("close", sa.Numeric(20, 6), nullable=True),
        sa.Column("pre_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("change", sa.Numeric(20, 6), nullable=True),
        sa.Column("pct_chg", sa.Numeric(20, 6), nullable=True),
        sa.Column("vol", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(24, 6), nullable=True),
        sa.Column("adj_factor", sa.Numeric(20, 6), nullable=True),
        sa.Column("adjustment_base_factor", sa.Numeric(20, 6), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dataset_code", "code", "trade_time"),
        postgresql_partition_by="RANGE (trade_time)",
    )
    op.create_index("ix_market_data_5m_dataset_trade_time", "market_data_5m", ["dataset_code", "trade_time"])

    op.create_table(
        "staging_market_data_5m",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("open", sa.Numeric(20, 6), nullable=True),
        sa.Column("high", sa.Numeric(20, 6), nullable=True),
        sa.Column("low", sa.Numeric(20, 6), nullable=True),
        sa.Column("close", sa.Numeric(20, 6), nullable=True),
        sa.Column("pre_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("change", sa.Numeric(20, 6), nullable=True),
        sa.Column("pct_chg", sa.Numeric(20, 6), nullable=True),
        sa.Column("vol", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(24, 6), nullable=True),
        sa.Column("adj_factor", sa.Numeric(20, 6), nullable=True),
        sa.Column("adjustment_base_factor", sa.Numeric(20, 6), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staging_market_data_5m_job_id", "staging_market_data_5m", ["job_id"])
    op.create_index(
        "ix_staging_market_data_5m_dataset_code_time",
        "staging_market_data_5m",
        ["dataset_code", "code", "trade_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_staging_market_data_5m_dataset_code_time", table_name="staging_market_data_5m")
    op.drop_index("ix_staging_market_data_5m_job_id", table_name="staging_market_data_5m")
    op.drop_table("staging_market_data_5m")
    op.drop_index("ix_market_data_5m_dataset_trade_time", table_name="market_data_5m")
    op.drop_table("market_data_5m")

    for table_name in ("market_data_1d", "staging_market_data_1m", "market_data_1m"):
        op.drop_column(table_name, "adjustment_base_factor")
