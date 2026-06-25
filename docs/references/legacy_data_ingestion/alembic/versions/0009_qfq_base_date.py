"""qfq base date

Revision ID: 0009_qfq_base_date
Revises: 0008_partition_date_idx
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0009_qfq_base_date"
down_revision: str | None = "0008_partition_date_idx"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

bar_table_names = (
    "market_data_1m",
    "staging_market_data_1m",
    "market_data_5m",
    "staging_market_data_5m",
    "market_data_1d",
)

official_table_names = (
    "market_data_1m",
    "market_data_5m",
    "market_data_1d",
)


def upgrade() -> None:
    for table_name in bar_table_names:
        op.add_column(table_name, sa.Column("qfq_base_date", sa.Date(), nullable=True))

    for table_name in official_table_names:
        op.execute(
            f"""
            UPDATE {table_name}
            SET qfq_base_date = date
            WHERE qfq_base_date IS NULL
            """
        )


def downgrade() -> None:
    for table_name in reversed(bar_table_names):
        op.drop_column(table_name, "qfq_base_date")
