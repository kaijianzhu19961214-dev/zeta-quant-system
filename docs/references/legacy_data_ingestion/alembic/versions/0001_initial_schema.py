"""initial schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("dataset_name", sa.String(length=128), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dataset_code"),
    )
    op.create_index("ix_datasets_dataset_code", "datasets", ["dataset_code"])

    op.create_table(
        "ingestion_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("file_path", sa.Text(), nullable=True),
        sa.Column("received_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inserted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skipped_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_ingestion_jobs_dataset_code", "ingestion_jobs", ["dataset_code"])
    op.create_index("ix_ingestion_jobs_job_id", "ingestion_jobs", ["job_id"])
    op.create_index("ix_ingestion_jobs_status", "ingestion_jobs", ["status"])

    op.create_table(
        "market_data_1m",
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("high_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("low_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(24, 6), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dataset_code", "symbol", "trade_time"),
        postgresql_partition_by="RANGE (trade_time)",
    )
    op.create_index(
        "ix_market_data_1m_dataset_trade_time",
        "market_data_1m",
        ["dataset_code", "trade_time"],
    )

    op.create_table(
        "staging_market_data_1m",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=64), nullable=False),
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("high_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("low_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(24, 6), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_staging_market_data_1m_job_id", "staging_market_data_1m", ["job_id"])
    op.create_index(
        "ix_staging_market_data_1m_dataset_symbol_time",
        "staging_market_data_1m",
        ["dataset_code", "symbol", "trade_time"],
    )


def downgrade() -> None:
    op.drop_index("ix_staging_market_data_1m_dataset_symbol_time", table_name="staging_market_data_1m")
    op.drop_index("ix_staging_market_data_1m_job_id", table_name="staging_market_data_1m")
    op.drop_table("staging_market_data_1m")
    op.drop_index("ix_market_data_1m_dataset_trade_time", table_name="market_data_1m")
    op.drop_table("market_data_1m")
    op.drop_index("ix_ingestion_jobs_status", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_job_id", table_name="ingestion_jobs")
    op.drop_index("ix_ingestion_jobs_dataset_code", table_name="ingestion_jobs")
    op.drop_table("ingestion_jobs")
    op.drop_index("ix_datasets_dataset_code", table_name="datasets")
    op.drop_table("datasets")
