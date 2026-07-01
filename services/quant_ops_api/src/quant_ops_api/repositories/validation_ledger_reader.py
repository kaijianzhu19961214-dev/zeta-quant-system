from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any

from sqlalchemy import BigInteger, Column, DateTime, MetaData, String, Table, Text, desc, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from quant_ops_api.schemas import ArtifactLedgerItem, TaskLedgerItem


validation_ledger_reader_metadata = MetaData()
SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

task_runs_table = Table(
    "task_runs",
    validation_ledger_reader_metadata,
    Column("id", BigInteger, primary_key=True),
    Column("task_id", String(128), nullable=False),
    Column("task_type", String(64), nullable=False),
    Column("task_name", String(256), nullable=False),
    Column("owner", String(128)),
    Column("status", String(32), nullable=False),
    Column("input_params", JSONB),
    Column("output_summary", JSONB),
    Column("error_message", Text),
    Column("created_at", DateTime(timezone=True)),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
)

task_artifacts_table = Table(
    "task_artifacts",
    validation_ledger_reader_metadata,
    Column("id", BigInteger, primary_key=True),
    Column("artifact_id", String(128), nullable=False),
    Column("task_id", String(128), nullable=False),
    Column("artifact_type", String(64), nullable=False),
    Column("storage_type", String(32), nullable=False),
    Column("bucket_name", String(128)),
    Column("object_key", Text),
    Column("uri", Text),
    Column("file_size_bytes", BigInteger),
    Column("metadata", JSONB),
    Column("created_at", DateTime(timezone=True)),
)

TASK_LEDGER_STATUSES = {
    "created",
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "canceled",
}


@dataclass(frozen=True)
class ValidationLedgerSnapshot:
    generated_at: datetime
    tasks: list[TaskLedgerItem]
    artifacts: list[ArtifactLedgerItem]


@dataclass(frozen=True)
class SqlAlchemyValidationLedgerReader:
    engine: AsyncEngine

    async def read_latest_snapshot(self, *, limit: int) -> ValidationLedgerSnapshot:
        normalized_limit = max(limit, 1)
        async with self.engine.connect() as connection:
            task_rows = (
                await connection.execute(
                    select(task_runs_table)
                    .order_by(
                        desc(task_runs_table.c.finished_at),
                        desc(task_runs_table.c.created_at),
                    )
                    .limit(normalized_limit)
                )
            ).mappings().all()

            task_ids = [_read_str(row=row, key="task_id") for row in task_rows]
            if not task_ids:
                return ValidationLedgerSnapshot(
                    generated_at=datetime.now(timezone.utc),
                    tasks=[],
                    artifacts=[],
                )

            artifact_rows = (
                await connection.execute(
                    select(task_artifacts_table)
                    .where(task_artifacts_table.c.task_id.in_(task_ids))
                    .order_by(
                        desc(task_artifacts_table.c.created_at),
                        desc(task_artifacts_table.c.id),
                    )
                )
            ).mappings().all()

        artifacts = [_build_artifact_ledger_item(row=row) for row in artifact_rows]
        artifact_count_by_task_id = Counter(artifact.task_id for artifact in artifacts)
        tasks = [
            _build_task_ledger_item(
                row=row,
                artifact_count=artifact_count_by_task_id[_read_str(row=row, key="task_id")],
            )
            for row in task_rows
        ]
        return ValidationLedgerSnapshot(
            generated_at=datetime.now(timezone.utc),
            tasks=tasks,
            artifacts=artifacts,
        )


def create_validation_ledger_reader_engine(
    *,
    database_url: str,
    schema_name: str | None = None,
) -> AsyncEngine:
    normalized_database_url = normalize_async_postgres_database_url(database_url=database_url)
    if normalized_database_url is None:
        raise ValueError("artifact ledger database URL must not be blank")

    normalized_schema_name = apply_validation_ledger_reader_schema(schema_name=schema_name)
    return create_async_engine(
        normalized_database_url,
        pool_pre_ping=True,
        connect_args=_build_connect_args(schema_name=normalized_schema_name),
    )


def normalize_async_postgres_database_url(*, database_url: str | None) -> str | None:
    if database_url is None or not database_url.strip():
        return None

    normalized_database_url = database_url.strip()
    if normalized_database_url.startswith("postgresql+asyncpg://"):
        return normalized_database_url

    for scheme in ("postgresql://", "postgres://"):
        if normalized_database_url.startswith(scheme):
            return f"postgresql+asyncpg://{normalized_database_url.removeprefix(scheme)}"

    return normalized_database_url


def normalize_database_schema_name(*, schema_name: str | None) -> str | None:
    if schema_name is None or not schema_name.strip():
        return None

    normalized_schema_name = schema_name.strip()
    if not SCHEMA_NAME_PATTERN.fullmatch(normalized_schema_name):
        raise ValueError("artifact ledger database schema name is invalid")
    return normalized_schema_name


def apply_validation_ledger_reader_schema(*, schema_name: str | None) -> str | None:
    normalized_schema_name = normalize_database_schema_name(schema_name=schema_name)
    for table in validation_ledger_reader_metadata.tables.values():
        table.schema = normalized_schema_name
    return normalized_schema_name


def _build_connect_args(*, schema_name: str | None) -> dict[str, Any]:
    if schema_name is None:
        return {}

    return {
        "server_settings": {
            "search_path": f"{schema_name},public",
        }
    }


def _build_task_ledger_item(
    *,
    row: Any,
    artifact_count: int,
) -> TaskLedgerItem:
    return TaskLedgerItem(
        task_id=_read_str(row=row, key="task_id"),
        task_type=_read_str(row=row, key="task_type"),
        task_name=_read_str(row=row, key="task_name"),
        owner=_read_optional_str(row=row, key="owner"),
        status=_normalize_status(value=_read_optional_str(row=row, key="status")),
        input_params=_read_dict(row=row, key="input_params"),
        output_summary=_read_dict(row=row, key="output_summary"),
        error_message=_read_optional_str(row=row, key="error_message"),
        created_at=_read_optional_datetime(row=row, key="created_at"),
        started_at=_read_optional_datetime(row=row, key="started_at"),
        finished_at=_read_optional_datetime(row=row, key="finished_at"),
        artifact_count=artifact_count,
    )


def _build_artifact_ledger_item(*, row: Any) -> ArtifactLedgerItem:
    metadata = _read_dict(row=row, key="metadata")
    return ArtifactLedgerItem(
        artifact_id=_read_str(row=row, key="artifact_id"),
        task_id=_read_str(row=row, key="task_id"),
        artifact_type=_read_str(row=row, key="artifact_type"),
        storage_type=_read_optional_str(row=row, key="storage_type") or "minio_s3",
        bucket_name=_read_optional_str(row=row, key="bucket_name"),
        object_key=_read_optional_str(row=row, key="object_key"),
        uri=_read_optional_str(row=row, key="uri"),
        file_size_bytes=_read_optional_int(row=row, key="file_size_bytes"),
        schema_version=_get_optional_str(value=metadata.get("schema_version")),
        metadata=metadata,
        created_at=_read_optional_datetime(row=row, key="created_at"),
    )


def _normalize_status(*, value: str | None) -> str:
    if value is None:
        return "pending"

    normalized_value = value.strip().lower()
    if normalized_value in TASK_LEDGER_STATUSES:
        return normalized_value
    return "pending"


def _read_str(*, row: Any, key: str) -> str:
    value = row.get(key)
    if isinstance(value, str) and value:
        return value
    return "unknown"


def _read_optional_str(*, row: Any, key: str) -> str | None:
    return _get_optional_str(value=row.get(key))


def _get_optional_str(*, value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _read_optional_int(*, row: Any, key: str) -> int | None:
    value = row.get(key)
    if isinstance(value, int):
        return value
    return None


def _read_dict(*, row: Any, key: str) -> dict[str, Any]:
    value = row.get(key)
    if isinstance(value, dict):
        return value
    return {}


def _read_optional_datetime(*, row: Any, key: str) -> datetime | None:
    value = row.get(key)
    if isinstance(value, datetime):
        return value
    return None
