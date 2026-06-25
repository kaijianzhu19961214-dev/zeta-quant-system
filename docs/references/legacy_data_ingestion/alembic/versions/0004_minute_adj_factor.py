"""minute adj factor

Revision ID: 0004_min_adj
Revises: 0003_source_names
Create Date: 2026-06-12
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_min_adj"
down_revision: str | None = "0003_source_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("market_data_1m", sa.Column("adj_factor", sa.Numeric(20, 6), nullable=True))
    op.add_column("staging_market_data_1m", sa.Column("adj_factor", sa.Numeric(20, 6), nullable=True))


def downgrade() -> None:
    op.drop_column("staging_market_data_1m", "adj_factor")
    op.drop_column("market_data_1m", "adj_factor")
