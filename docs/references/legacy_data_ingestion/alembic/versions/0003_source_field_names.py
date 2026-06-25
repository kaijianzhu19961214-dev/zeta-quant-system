"""source field names

Revision ID: 0003_source_names
Revises: 0002_bar_dims
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003_source_names"
down_revision: str | None = "0002_bar_dims"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("trading_calendar", "trade_date", new_column_name="date")

    for table_name in ("market_data_1m", "staging_market_data_1m"):
        op.alter_column(table_name, "symbol", new_column_name="code")
        op.alter_column(table_name, "trade_date", new_column_name="date")
        op.alter_column(table_name, "open_price", new_column_name="open")
        op.alter_column(table_name, "high_price", new_column_name="high")
        op.alter_column(table_name, "low_price", new_column_name="low")
        op.alter_column(table_name, "close_price", new_column_name="close")
        op.alter_column(table_name, "volume", new_column_name="vol")

    op.alter_column("market_data_1d", "symbol", new_column_name="code")
    op.alter_column("market_data_1d", "trade_date", new_column_name="date")
    op.alter_column("market_data_1d", "open_price", new_column_name="open")
    op.alter_column("market_data_1d", "high_price", new_column_name="high")
    op.alter_column("market_data_1d", "low_price", new_column_name="low")
    op.alter_column("market_data_1d", "close_price", new_column_name="close")
    op.alter_column("market_data_1d", "volume", new_column_name="vol")

    op.execute("ALTER INDEX IF EXISTS ix_market_data_1d_dataset_trade_date RENAME TO ix_market_data_1d_dataset_date")
    op.execute(
        "ALTER INDEX IF EXISTS ix_staging_market_data_1m_dataset_symbol_time "
        "RENAME TO ix_staging_market_data_1m_dataset_code_time"
    )


def downgrade() -> None:
    op.execute(
        "ALTER INDEX IF EXISTS ix_staging_market_data_1m_dataset_code_time "
        "RENAME TO ix_staging_market_data_1m_dataset_symbol_time"
    )
    op.execute("ALTER INDEX IF EXISTS ix_market_data_1d_dataset_date RENAME TO ix_market_data_1d_dataset_trade_date")

    op.alter_column("market_data_1d", "vol", new_column_name="volume")
    op.alter_column("market_data_1d", "close", new_column_name="close_price")
    op.alter_column("market_data_1d", "low", new_column_name="low_price")
    op.alter_column("market_data_1d", "high", new_column_name="high_price")
    op.alter_column("market_data_1d", "open", new_column_name="open_price")
    op.alter_column("market_data_1d", "date", new_column_name="trade_date")
    op.alter_column("market_data_1d", "code", new_column_name="symbol")

    for table_name in ("staging_market_data_1m", "market_data_1m"):
        op.alter_column(table_name, "vol", new_column_name="volume")
        op.alter_column(table_name, "close", new_column_name="close_price")
        op.alter_column(table_name, "low", new_column_name="low_price")
        op.alter_column(table_name, "high", new_column_name="high_price")
        op.alter_column(table_name, "open", new_column_name="open_price")
        op.alter_column(table_name, "date", new_column_name="trade_date")
        op.alter_column(table_name, "code", new_column_name="symbol")

    op.alter_column("trading_calendar", "date", new_column_name="trade_date")
