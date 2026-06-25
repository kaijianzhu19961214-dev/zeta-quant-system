"""existing partition date indexes

Revision ID: 0008_partition_date_idx
Revises: 0007_minute_query_indexes
Create Date: 2026-06-17
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008_partition_date_idx"
down_revision: str | None = "0007_minute_query_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            partition_record record;
            target_index_name text;
        BEGIN
            FOR partition_record IN
                SELECT child.relname AS partition_name
                FROM pg_inherits
                JOIN pg_class child ON child.oid = pg_inherits.inhrelid
                JOIN pg_class parent ON parent.oid = pg_inherits.inhparent
                WHERE parent.relname IN ('market_data_1m', 'market_data_5m')
            LOOP
                target_index_name := 'ix_' || partition_record.partition_name || '_dataset_date_code';
                EXECUTE format(
                    'CREATE INDEX IF NOT EXISTS %I ON %I (dataset_code, date, code)',
                    target_index_name,
                    partition_record.partition_name
                );
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            index_record record;
        BEGIN
            FOR index_record IN
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND (
                      tablename LIKE 'market_data_1m_%'
                      OR tablename LIKE 'market_data_5m_%'
                  )
                  AND indexname LIKE 'ix_%_dataset_date_code'
            LOOP
                EXECUTE format('DROP INDEX IF EXISTS %I', index_record.indexname);
            END LOOP;
        END $$;
        """
    )
