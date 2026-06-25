"""task runs and artifacts

Revision ID: 0011_task_runs
Revises: 0010_factor_batches
Create Date: 2026-06-18
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0011_task_runs"
down_revision: str | None = "0010_factor_batches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "task_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("task_name", sa.String(length=256), nullable=False),
        sa.Column("owner", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("input_params", postgresql.JSONB(), nullable=True),
        sa.Column("output_summary", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id"),
    )
    op.create_index("ix_task_runs_task_id", "task_runs", ["task_id"])
    op.create_index("ix_task_runs_status", "task_runs", ["status"])
    op.create_index("ix_task_runs_type_status_created", "task_runs", ["task_type", "status", "created_at"])
    op.create_index("ix_task_runs_owner_created", "task_runs", ["owner", "created_at"])

    op.create_table(
        "task_artifacts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("artifact_name", sa.String(length=256), nullable=True),
        sa.Column("storage_type", sa.String(length=32), server_default="minio", nullable=False),
        sa.Column("bucket_name", sa.String(length=128), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("uri", sa.Text(), nullable=False),
        sa.Column("content_type", sa.String(length=128), nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("etag", sa.String(length=128), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artifact_id"),
    )
    op.create_index("ix_task_artifacts_task_id", "task_artifacts", ["task_id"])
    op.create_index("ix_task_artifacts_type_created", "task_artifacts", ["artifact_type", "created_at"])
    op.create_index("ix_task_artifacts_bucket_object", "task_artifacts", ["bucket_name", "object_key"])


def downgrade() -> None:
    op.drop_index("ix_task_artifacts_bucket_object", table_name="task_artifacts")
    op.drop_index("ix_task_artifacts_type_created", table_name="task_artifacts")
    op.drop_index("ix_task_artifacts_task_id", table_name="task_artifacts")
    op.drop_table("task_artifacts")

    op.drop_index("ix_task_runs_owner_created", table_name="task_runs")
    op.drop_index("ix_task_runs_type_status_created", table_name="task_runs")
    op.drop_index("ix_task_runs_status", table_name="task_runs")
    op.drop_index("ix_task_runs_task_id", table_name="task_runs")
    op.drop_table("task_runs")
