"""security calendar and bar fields

Revision ID: 0002_bar_dims
Revises: 0001_initial_schema
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_bar_dims"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "securities",
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("area", sa.String(length=64), nullable=True),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("fullname", sa.String(length=256), nullable=False),
        sa.Column("enname", sa.String(length=256), nullable=False),
        sa.Column("cnspell", sa.String(length=64), nullable=False),
        sa.Column("market", sa.String(length=64), nullable=False),
        sa.Column("exchange", sa.String(length=16), nullable=False),
        sa.Column("curr_type", sa.String(length=16), nullable=False),
        sa.Column("list_status", sa.String(length=8), nullable=False),
        sa.Column("list_date", sa.Date(), nullable=False),
        sa.Column("delist_date", sa.Date(), nullable=True),
        sa.Column("is_hs", sa.String(length=8), nullable=False),
        sa.Column("act_name", sa.String(length=256), nullable=True),
        sa.Column("act_ent_type", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("code"),
    )
    op.create_index("ix_securities_exchange", "securities", ["exchange"])
    op.create_index("ix_securities_industry", "securities", ["industry"])
    op.create_index("ix_securities_list_status", "securities", ["list_status"])
    op.create_index("ix_securities_name", "securities", ["name"])
    op.create_index("ix_securities_symbol", "securities", ["symbol"])

    op.create_table(
        "trading_calendar",
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("trade_date"),
    )

    for table_name in ("market_data_1m", "staging_market_data_1m"):
        op.add_column(table_name, sa.Column("pre_close", sa.Numeric(20, 6), nullable=True))
        op.add_column(table_name, sa.Column("change", sa.Numeric(20, 6), nullable=True))
        op.add_column(table_name, sa.Column("pct_chg", sa.Numeric(20, 6), nullable=True))

    op.create_table(
        "market_data_1d",
        sa.Column("dataset_code", sa.String(length=64), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("high_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("low_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("close_price", sa.Numeric(20, 6), nullable=True),
        sa.Column("pre_close", sa.Numeric(20, 6), nullable=True),
        sa.Column("change", sa.Numeric(20, 6), nullable=True),
        sa.Column("pct_chg", sa.Numeric(20, 6), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(24, 6), nullable=True),
        sa.Column("adj_factor", sa.Numeric(20, 6), nullable=True),
        sa.Column("vwap", sa.Numeric(20, 6), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("dataset_code", "symbol", "trade_date"),
        postgresql_partition_by="RANGE (trade_date)",
    )
    op.create_index("ix_market_data_1d_dataset_trade_date", "market_data_1d", ["dataset_code", "trade_date"])


def downgrade() -> None:
    op.drop_index("ix_market_data_1d_dataset_trade_date", table_name="market_data_1d")
    op.drop_table("market_data_1d")

    for table_name in ("staging_market_data_1m", "market_data_1m"):
        op.drop_column(table_name, "pct_chg")
        op.drop_column(table_name, "change")
        op.drop_column(table_name, "pre_close")

    op.drop_table("trading_calendar")
    op.drop_index("ix_securities_symbol", table_name="securities")
    op.drop_index("ix_securities_name", table_name="securities")
    op.drop_index("ix_securities_list_status", table_name="securities")
    op.drop_index("ix_securities_industry", table_name="securities")
    op.drop_index("ix_securities_exchange", table_name="securities")
    op.drop_table("securities")
