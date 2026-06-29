from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from quant_contracts import FactorValidationManifest, TaskArtifact
from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from quant_factor_validation.services.validation_persistence import ValidationPersistenceError

validation_ledger_metadata = MetaData()

task_runs_table = Table(
    "task_runs",
    validation_ledger_metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("task_id", String(128), nullable=False),
    Column("task_type", String(64), nullable=False),
    Column("task_name", String(256), nullable=False),
    Column("owner", String(128)),
    Column("status", String(32), nullable=False),
    Column("description", Text),
    Column("input_params", JSONB),
    Column("output_summary", JSONB),
    Column("error_message", Text),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("started_at", DateTime(timezone=True)),
    Column("finished_at", DateTime(timezone=True)),
    UniqueConstraint("task_id", name="uq_task_runs_task_id"),
    Index("ix_task_runs_task_id", "task_id"),
    Index("ix_task_runs_status", "status"),
    Index("ix_task_runs_type_status_created", "task_type", "status", "created_at"),
    Index("ix_task_runs_owner_created", "owner", "created_at"),
)

task_artifacts_table = Table(
    "task_artifacts",
    validation_ledger_metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("artifact_id", String(128), nullable=False),
    Column("task_id", String(128), nullable=False),
    Column("artifact_type", String(64), nullable=False),
    Column("artifact_name", String(256)),
    Column("storage_type", String(32), server_default="minio_s3", nullable=False),
    Column("bucket_name", String(128), nullable=False),
    Column("object_key", Text, nullable=False),
    Column("uri", Text, nullable=False),
    Column("content_type", String(128)),
    Column("file_size_bytes", BigInteger),
    Column("etag", String(128)),
    Column("metadata", JSONB),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    UniqueConstraint("artifact_id", name="uq_task_artifacts_artifact_id"),
    Index("ix_task_artifacts_task_id", "task_id"),
    Index("ix_task_artifacts_type_created", "artifact_type", "created_at"),
    Index("ix_task_artifacts_bucket_object", "bucket_name", "object_key"),
)


class AsyncSessionContext(Protocol):
    async def __aenter__(self) -> AsyncSession:
        raise NotImplementedError

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> bool | None:
        raise NotImplementedError


class AsyncSessionFactory(Protocol):
    def __call__(self) -> AsyncSessionContext:
        raise NotImplementedError


@dataclass(frozen=True)
class SqlAlchemyValidationLedgerRepository:
    session_factory: AsyncSessionFactory

    async def record_validation_manifest(
        self,
        *,
        manifest: FactorValidationManifest,
    ) -> FactorValidationManifest:
        try:
            async with self.session_factory() as session:
                await session.execute(_build_task_run_upsert_statement(manifest=manifest))
                for artifact in manifest.artifacts:
                    await session.execute(_build_task_artifact_upsert_statement(artifact=artifact))
                await session.commit()
        except SQLAlchemyError as error:
            raise ValidationPersistenceError("failed to record validation manifest ledger") from error

        return manifest


def create_validation_database_engine(
    *,
    database_url: str,
    echo: bool = False,
) -> AsyncEngine:
    normalized_database_url = database_url.strip()
    if not normalized_database_url:
        raise ValueError("validation database URL must not be blank")

    return create_async_engine(
        normalized_database_url,
        echo=echo,
        pool_pre_ping=True,
    )


def create_validation_session_factory(
    *,
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def create_validation_ledger_schema(*, engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(validation_ledger_metadata.create_all)


def _build_task_run_values(*, manifest: FactorValidationManifest) -> dict[str, Any]:
    task_run = manifest.task_run
    values: dict[str, Any] = {
        "task_id": task_run.task_id,
        "task_type": task_run.task_type,
        "task_name": task_run.task_name,
        "owner": task_run.owner,
        "status": str(task_run.status),
        "description": None,
        "input_params": task_run.input_params,
        "output_summary": task_run.output_summary,
        "error_message": task_run.error_message,
        "started_at": task_run.started_at,
        "finished_at": task_run.finished_at,
    }
    if task_run.created_at is not None:
        values["created_at"] = task_run.created_at

    return values


def _build_task_artifact_values(*, artifact: TaskArtifact) -> dict[str, Any]:
    metadata = artifact.metadata
    return {
        "artifact_id": artifact.artifact_id,
        "task_id": artifact.task_id,
        "artifact_type": str(artifact.artifact_type),
        "artifact_name": artifact.artifact_id,
        "storage_type": _get_optional_str(metadata.get("object_store")) or "minio_s3",
        "bucket_name": _require_artifact_field(
            artifact_id=artifact.artifact_id,
            field_name="bucket_name",
            value=artifact.bucket_name,
        ),
        "object_key": _require_artifact_field(
            artifact_id=artifact.artifact_id,
            field_name="object_key",
            value=artifact.object_key,
        ),
        "uri": _require_artifact_field(
            artifact_id=artifact.artifact_id,
            field_name="uri",
            value=artifact.uri,
        ),
        "content_type": _get_optional_str(metadata.get("content_type")),
        "file_size_bytes": artifact.file_size_bytes,
        "etag": _get_optional_str(metadata.get("etag")),
        "metadata": metadata,
        "created_at": artifact.created_at,
    }


def _build_task_run_upsert_statement(*, manifest: FactorValidationManifest) -> Any:
    values = _build_task_run_values(manifest=manifest)
    insert_statement = postgresql_insert(task_runs_table).values(**values)
    return insert_statement.on_conflict_do_update(
        index_elements=[task_runs_table.c.task_id],
        set_={
            "task_type": insert_statement.excluded.task_type,
            "task_name": insert_statement.excluded.task_name,
            "owner": insert_statement.excluded.owner,
            "status": insert_statement.excluded.status,
            "description": insert_statement.excluded.description,
            "input_params": insert_statement.excluded.input_params,
            "output_summary": insert_statement.excluded.output_summary,
            "error_message": insert_statement.excluded.error_message,
            "updated_at": func.now(),
            "started_at": insert_statement.excluded.started_at,
            "finished_at": insert_statement.excluded.finished_at,
        },
    )


def _build_task_artifact_upsert_statement(*, artifact: TaskArtifact) -> Any:
    values = _build_task_artifact_values(artifact=artifact)
    insert_statement = postgresql_insert(task_artifacts_table).values(**values)
    return insert_statement.on_conflict_do_update(
        index_elements=[task_artifacts_table.c.artifact_id],
        set_={
            "task_id": insert_statement.excluded.task_id,
            "artifact_type": insert_statement.excluded.artifact_type,
            "artifact_name": insert_statement.excluded.artifact_name,
            "storage_type": insert_statement.excluded.storage_type,
            "bucket_name": insert_statement.excluded.bucket_name,
            "object_key": insert_statement.excluded.object_key,
            "uri": insert_statement.excluded.uri,
            "content_type": insert_statement.excluded.content_type,
            "file_size_bytes": insert_statement.excluded.file_size_bytes,
            "etag": insert_statement.excluded.etag,
            "metadata": insert_statement.excluded["metadata"],
        },
    )


def _require_artifact_field(
    *,
    artifact_id: str,
    field_name: str,
    value: str | None,
) -> str:
    if value:
        return value

    raise ValidationPersistenceError(f"artifact {artifact_id} is missing {field_name}")


def _get_optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
