from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import Any, Protocol

from quant_contracts import AlgorithmReviewGateEvidenceRecord
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Index,
    MetaData,
    String,
    Table,
    Text,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB, insert as postgresql_insert
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine


algorithm_review_metadata = MetaData()
SCHEMA_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

algorithm_review_gate_evidence_table = Table(
    "algorithm_review_gate_evidence",
    algorithm_review_metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("evidence_id", String(128), nullable=False, unique=True),
    Column("algorithm_id", String(128), nullable=False),
    Column("gate_id", String(64), nullable=False),
    Column("gate_category", String(32), nullable=False),
    Column("gate_title", String(128), nullable=False),
    Column("previous_gate_status", String(32), nullable=False),
    Column("evidence_status", String(32), nullable=False),
    Column("submitted_by", String(128), nullable=False),
    Column("evidence_type", String(32), nullable=False),
    Column("evidence_source", Text, nullable=False),
    Column("summary", Text, nullable=False),
    Column("artifact_id", String(128)),
    Column("artifact_uri", Text),
    Column("source_url", Text),
    Column("notes", JSONB),
    Column("submitted_at", DateTime(timezone=True), nullable=False),
    Column("reviewed_by", String(128)),
    Column("reviewed_at", DateTime(timezone=True)),
    Column("review_comment", Text),
    Column("is_required", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Column("updated_at", DateTime(timezone=True), server_default=func.now(), nullable=False),
    Index("ix_algorithm_review_gate_evidence_id", "evidence_id"),
    Index("ix_algorithm_review_gate_evidence_algorithm_gate", "algorithm_id", "gate_id", "submitted_at"),
    Index("ix_algorithm_review_gate_evidence_status", "evidence_status", "submitted_at"),
    Index("ix_algorithm_review_gate_evidence_artifact_id", "artifact_id"),
)


class AlgorithmReviewEvidenceRepositoryError(Exception):
    pass


class AlgorithmReviewEvidenceNotFoundError(AlgorithmReviewEvidenceRepositoryError):
    pass


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
class SqlAlchemyAlgorithmReviewEvidenceRepository:
    session_factory: AsyncSessionFactory

    async def record_evidence(
        self,
        *,
        record: AlgorithmReviewGateEvidenceRecord,
    ) -> AlgorithmReviewGateEvidenceRecord:
        try:
            async with self.session_factory() as session:
                await session.execute(_build_evidence_upsert_statement(record=record))
                await session.commit()
        except SQLAlchemyError as error:
            raise AlgorithmReviewEvidenceRepositoryError("failed to record algorithm review evidence") from error

        return record

    async def list_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> list[AlgorithmReviewGateEvidenceRecord]:
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    _build_evidence_select_statement(
                        algorithm_id=algorithm_id,
                        gate_id=gate_id,
                        limit=limit,
                    )
                )
                rows = result.mappings().all()
        except SQLAlchemyError as error:
            raise AlgorithmReviewEvidenceRepositoryError("failed to list algorithm review evidence") from error

        return [_build_record_from_row(row=dict(row)) for row in rows]

    async def review_evidence(
        self,
        *,
        evidence_id: str,
        evidence_status: str,
        reviewed_by: str,
        reviewed_at: datetime,
        review_comment: str | None = None,
    ) -> AlgorithmReviewGateEvidenceRecord:
        try:
            async with self.session_factory() as session:
                result = await session.execute(
                    _build_evidence_review_statement(
                        evidence_id=evidence_id,
                        evidence_status=evidence_status,
                        reviewed_by=reviewed_by,
                        reviewed_at=reviewed_at,
                        review_comment=review_comment,
                    )
                )
                row = result.mappings().first()
                if row is None:
                    raise AlgorithmReviewEvidenceNotFoundError(f"algorithm review evidence not found: {evidence_id}")
                await session.commit()
        except AlgorithmReviewEvidenceNotFoundError:
            raise
        except SQLAlchemyError as error:
            raise AlgorithmReviewEvidenceRepositoryError("failed to review algorithm review evidence") from error

        return _build_record_from_row(row=dict(row))


def create_algorithm_review_database_engine(
    *,
    database_url: str,
    echo: bool = False,
    schema_name: str | None = None,
) -> AsyncEngine:
    normalized_database_url = database_url.strip()
    if not normalized_database_url:
        raise ValueError("algorithm review database URL must not be blank")

    normalized_schema_name = apply_algorithm_review_schema(schema_name=schema_name)
    return create_async_engine(
        normalized_database_url,
        echo=echo,
        pool_pre_ping=True,
        connect_args=_build_connect_args(schema_name=normalized_schema_name),
    )


def create_algorithm_review_session_factory(
    *,
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )


async def create_algorithm_review_evidence_schema(
    *,
    engine: AsyncEngine,
    schema_name: str | None = None,
) -> None:
    normalized_schema_name = apply_algorithm_review_schema(schema_name=schema_name)
    async with engine.begin() as connection:
        if normalized_schema_name is not None:
            await connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{normalized_schema_name}"'))
        await connection.run_sync(algorithm_review_metadata.create_all)


def normalize_database_schema_name(*, schema_name: str | None) -> str | None:
    if schema_name is None or not schema_name.strip():
        return None

    normalized_schema_name = schema_name.strip()
    if not SCHEMA_NAME_PATTERN.fullmatch(normalized_schema_name):
        raise ValueError("algorithm review database schema name is invalid")
    return normalized_schema_name


def apply_algorithm_review_schema(*, schema_name: str | None) -> str | None:
    normalized_schema_name = normalize_database_schema_name(schema_name=schema_name)
    for table in algorithm_review_metadata.tables.values():
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


def _build_evidence_values(*, record: AlgorithmReviewGateEvidenceRecord) -> dict[str, Any]:
    return {
        "evidence_id": record.evidence_id,
        "algorithm_id": record.algorithm_id,
        "gate_id": record.gate_id,
        "gate_category": record.gate_category,
        "gate_title": record.gate_title,
        "previous_gate_status": record.previous_gate_status,
        "evidence_status": record.evidence_status,
        "submitted_by": record.submitted_by,
        "evidence_type": record.evidence_type,
        "evidence_source": record.evidence_source,
        "summary": record.summary,
        "artifact_id": record.artifact_id,
        "artifact_uri": record.artifact_uri,
        "source_url": record.source_url,
        "notes": record.notes,
        "submitted_at": record.submitted_at,
        "reviewed_by": record.reviewed_by,
        "reviewed_at": record.reviewed_at,
        "review_comment": record.review_comment,
        "is_required": record.is_required,
    }


def _build_evidence_upsert_statement(*, record: AlgorithmReviewGateEvidenceRecord) -> Any:
    values = _build_evidence_values(record=record)
    insert_statement = postgresql_insert(algorithm_review_gate_evidence_table).values(**values)
    return insert_statement.on_conflict_do_update(
        index_elements=[algorithm_review_gate_evidence_table.c.evidence_id],
        set_={
            "algorithm_id": insert_statement.excluded.algorithm_id,
            "gate_id": insert_statement.excluded.gate_id,
            "gate_category": insert_statement.excluded.gate_category,
            "gate_title": insert_statement.excluded.gate_title,
            "previous_gate_status": insert_statement.excluded.previous_gate_status,
            "evidence_status": insert_statement.excluded.evidence_status,
            "submitted_by": insert_statement.excluded.submitted_by,
            "evidence_type": insert_statement.excluded.evidence_type,
            "evidence_source": insert_statement.excluded.evidence_source,
            "summary": insert_statement.excluded.summary,
            "artifact_id": insert_statement.excluded.artifact_id,
            "artifact_uri": insert_statement.excluded.artifact_uri,
            "source_url": insert_statement.excluded.source_url,
            "notes": insert_statement.excluded.notes,
            "submitted_at": insert_statement.excluded.submitted_at,
            "reviewed_by": insert_statement.excluded.reviewed_by,
            "reviewed_at": insert_statement.excluded.reviewed_at,
            "review_comment": insert_statement.excluded.review_comment,
            "is_required": insert_statement.excluded.is_required,
            "updated_at": func.now(),
        },
    )


def _build_evidence_select_statement(
    *,
    algorithm_id: str,
    gate_id: str | None,
    limit: int,
) -> Any:
    statement = (
        select(algorithm_review_gate_evidence_table)
        .where(algorithm_review_gate_evidence_table.c.algorithm_id == algorithm_id)
        .order_by(algorithm_review_gate_evidence_table.c.submitted_at.desc())
        .limit(limit)
    )
    if gate_id is None:
        return statement
    return statement.where(algorithm_review_gate_evidence_table.c.gate_id == gate_id)


def _build_evidence_review_statement(
    *,
    evidence_id: str,
    evidence_status: str,
    reviewed_by: str,
    reviewed_at: datetime,
    review_comment: str | None,
) -> Any:
    return (
        update(algorithm_review_gate_evidence_table)
        .where(algorithm_review_gate_evidence_table.c.evidence_id == evidence_id)
        .values(
            evidence_status=evidence_status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            review_comment=review_comment,
            updated_at=func.now(),
        )
        .returning(algorithm_review_gate_evidence_table)
    )


def _build_record_from_row(*, row: dict[str, Any]) -> AlgorithmReviewGateEvidenceRecord:
    return AlgorithmReviewGateEvidenceRecord(
        evidence_id=row["evidence_id"],
        algorithm_id=row["algorithm_id"],
        gate_id=row["gate_id"],
        gate_category=row["gate_category"],
        gate_title=row["gate_title"],
        previous_gate_status=row["previous_gate_status"],
        evidence_status=row["evidence_status"],
        submitted_by=row["submitted_by"],
        evidence_type=row["evidence_type"],
        evidence_source=row["evidence_source"],
        summary=row["summary"],
        artifact_id=row["artifact_id"],
        artifact_uri=row["artifact_uri"],
        source_url=row["source_url"],
        notes=row["notes"] or [],
        submitted_at=row["submitted_at"],
        reviewed_by=row["reviewed_by"],
        reviewed_at=row["reviewed_at"],
        review_comment=row["review_comment"],
        is_required=row["is_required"],
    )
