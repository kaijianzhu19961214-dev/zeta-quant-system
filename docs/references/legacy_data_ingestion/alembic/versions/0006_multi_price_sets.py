"""multi price sets

Revision ID: 0006_multi_price_sets
Revises: 0005_qfq_5m
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0006_multi_price_sets"
down_revision: str | None = "0005_qfq_5m"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

bar_table_names = (
    "market_data_1m",
    "staging_market_data_1m",
    "market_data_5m",
    "staging_market_data_5m",
    "market_data_1d",
)

price_field_names = ("open", "high", "low", "close", "pre_close", "change")


def add_factor_columns(table_name: str) -> None:
    op.add_column(table_name, sa.Column("qfq_factor", sa.Numeric(24, 10), nullable=True))
    op.add_column(table_name, sa.Column("hfq_factor", sa.Numeric(24, 10), nullable=True))


def drop_factor_columns(table_name: str) -> None:
    op.drop_column(table_name, "hfq_factor")
    op.drop_column(table_name, "qfq_factor")


def add_price_set_columns(table_name: str) -> None:
    for prefix in ("qfq", "hfq"):
        for field_name in price_field_names:
            op.add_column(table_name, sa.Column(f"{prefix}_{field_name}", sa.Numeric(20, 6), nullable=True))


def drop_price_set_columns(table_name: str) -> None:
    for prefix in ("hfq", "qfq"):
        for field_name in reversed(price_field_names):
            op.drop_column(table_name, f"{prefix}_{field_name}")


def upgrade() -> None:
    for table_name in bar_table_names:
        op.drop_column(table_name, "adjustment_base_factor")
        add_factor_columns(table_name)
        add_price_set_columns(table_name)

    op.add_column("market_data_1d", sa.Column("qfq_vwap", sa.Numeric(20, 6), nullable=True))
    op.add_column("market_data_1d", sa.Column("hfq_vwap", sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("market_data_1d", "hfq_vwap")
    op.drop_column("market_data_1d", "qfq_vwap")

    for table_name in reversed(bar_table_names):
        drop_price_set_columns(table_name)
        drop_factor_columns(table_name)
        op.add_column(table_name, sa.Column("adjustment_base_factor", sa.Numeric(20, 6), nullable=True))
