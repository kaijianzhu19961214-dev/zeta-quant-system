"""minute query indexes

Revision ID: 0007_minute_query_indexes
Revises: 0006_multi_price_sets
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007_minute_query_indexes"
down_revision: str | None = "0006_multi_price_sets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_market_data_1m_dataset_date_code",
        "market_data_1m",
        ["dataset_code", "date", "code"],
    )
    op.create_index(
        "ix_market_data_5m_dataset_date_code",
        "market_data_5m",
        ["dataset_code", "date", "code"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_data_5m_dataset_date_code", table_name="market_data_5m")
    op.drop_index("ix_market_data_1m_dataset_date_code", table_name="market_data_1m")
