from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
import os
import sys

from minio import Minio
from quant_contracts import (
    FactorDailyValue,
    FactorValidationManifest,
    FactorValidationRequest,
    FactorValidationResponse,
    MarketBar,
    MarketBarsMeta,
    MarketBarsQuery,
    MarketBarsResponse,
)
from sqlalchemy import func, select

from quant_factor_validation.integrations import MinioValidationArtifactStore, create_minio_client
from quant_factor_validation.repositories.validation_ledger import (
    AsyncSessionFactory,
    SqlAlchemyValidationLedgerRepository,
    create_validation_database_engine,
    create_validation_ledger_schema,
    create_validation_session_factory,
    task_artifacts_table,
    task_runs_table,
)
from quant_factor_validation.services import FactorValidationService, ValidationPersistenceService


DEFAULT_BUCKET_NAME = "quant-factor-data"
DEFAULT_RUN_ID = "validation_smoke_local"
EXPECTED_ARTIFACT_SCHEMA_VERSIONS = frozenset(
    {
        "factor_validation_report.v1",
        "factor_validation_metrics.v1",
        "factor_ic_series.v1",
        "factor_group_returns.v1",
        "factor_score_card.v1",
        "factor_comparison_report.v1",
    }
)
EXPECTED_ARTIFACT_FILE_NAMES = frozenset(
    {
        "validation_report.json",
        "metrics.json",
        "ic_series.json",
        "group_returns.json",
        "score_card.json",
        "comparison_report.json",
    }
)


@dataclass(frozen=True)
class PersistenceSmokeConfig:
    database_url: str
    object_store_endpoint: str
    object_store_access_key: str
    object_store_secret_key: str
    object_store_bucket: str = DEFAULT_BUCKET_NAME
    object_store_secure: bool = False
    should_create_schema: bool = True
    should_create_bucket: bool = False
    run_id: str = DEFAULT_RUN_ID


@dataclass(frozen=True)
class LedgerCounts:
    task_count: int
    artifact_count: int


class SmokeMarketDataReader:
    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=query.timeframe,
                price_mode=query.price_mode,
                row_count=4,
                dataset_code=query.dataset_code or "smoke_market",
                batch_id=query.batch_id,
            ),
            rows=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-16", close_price="11"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-16", close_price="12"),
            ],
        )


async def run_persistence_smoke(*, config: PersistenceSmokeConfig) -> list[str]:
    minio_client = create_minio_client(
        endpoint=config.object_store_endpoint,
        access_key=config.object_store_access_key,
        secret_key=config.object_store_secret_key,
        secure=config.object_store_secure,
    )
    await ensure_bucket_exists(client=minio_client, config=config)

    engine = create_validation_database_engine(database_url=config.database_url)
    try:
        if config.should_create_schema:
            await create_validation_ledger_schema(engine=engine)

        session_factory = create_validation_session_factory(engine=engine)
        service = FactorValidationService(
            market_data_reader=SmokeMarketDataReader(),
            persistence_service=ValidationPersistenceService(
                is_enabled=True,
                artifact_store=MinioValidationArtifactStore(
                    client=minio_client,
                    bucket_name=config.object_store_bucket,
                ),
                ledger_repository=SqlAlchemyValidationLedgerRepository(session_factory=session_factory),
            ),
        )
        response = await service.validate(request=build_smoke_request(run_id=config.run_id))
        manifest = validate_persisted_response(response=response)
        counts = await count_ledger_rows(
            session_factory=session_factory,
            task_id=manifest.task_run.task_id,
        )
        validate_ledger_counts(counts=counts, expected_artifact_count=len(manifest.artifacts))
        await validate_object_store_objects(
            client=minio_client,
            manifest=manifest,
        )
    finally:
        await engine.dispose()

    return [
        f"manifest persisted: {manifest.manifest_id}",
        f"postgres ledger ok: task_count={counts.task_count}, artifact_count={counts.artifact_count}",
        f"object store ok: bucket={config.object_store_bucket}, object_count={len(manifest.artifacts)}",
    ]


def build_smoke_request(*, run_id: str) -> FactorValidationRequest:
    return FactorValidationRequest(
        factor_name="smoke_momentum_1d",
        factor_values=[
            FactorDailyValue(
                symbol="000001.SZ",
                trade_date=date(2026, 3, 13),
                factor_name="smoke_momentum_1d",
                factor_value="0.1",
            ),
            FactorDailyValue(
                symbol="000002.SZ",
                trade_date=date(2026, 3, 13),
                factor_name="smoke_momentum_1d",
                factor_value="0.2",
            ),
        ],
        market_start=date(2026, 3, 13),
        market_end=date(2026, 3, 16),
        forward_days=1,
        group_count=2,
        dataset_code="smoke_market",
        run_id=run_id,
    )


def validate_persisted_response(*, response: FactorValidationResponse) -> FactorValidationManifest:
    manifest = response.manifest
    if manifest is None:
        raise RuntimeError("validation response did not include manifest")
    if manifest.persistence_status != "persisted":
        raise RuntimeError(f"manifest persistence_status is {manifest.persistence_status}")
    if response.metrics.effective_sample_count < 1:
        raise RuntimeError("smoke validation produced no effective samples")

    validate_manifest_artifacts(manifest=manifest)

    return manifest


def validate_manifest_artifacts(*, manifest: FactorValidationManifest) -> None:
    expected_artifact_count = len(EXPECTED_ARTIFACT_SCHEMA_VERSIONS)
    if len(manifest.artifacts) != expected_artifact_count:
        raise RuntimeError(f"expected {expected_artifact_count} artifacts, got {len(manifest.artifacts)}")

    schema_versions: set[str] = set()
    file_names: set[str] = set()

    for artifact in manifest.artifacts:
        if artifact.bucket_name is None:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing bucket_name")
        if artifact.object_key is None:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing object_key")
        if artifact.uri is None:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing uri")
        if artifact.file_size_bytes is None or artifact.file_size_bytes <= 0:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing file_size_bytes")
        if artifact.metadata.get("content_type") != "application/json":
            raise RuntimeError(f"artifact {artifact.artifact_id} content_type is not application/json")
        if not artifact.metadata.get("sha256"):
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing sha256")
        if artifact.metadata.get("persistence_status") != "persisted":
            raise RuntimeError(f"artifact {artifact.artifact_id} was not marked persisted")

        schema_version = artifact.metadata.get("schema_version")
        if not isinstance(schema_version, str) or not schema_version:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing schema_version")

        schema_versions.add(schema_version)
        file_names.add(artifact.object_key.rsplit("/", 1)[-1])

    if schema_versions != EXPECTED_ARTIFACT_SCHEMA_VERSIONS:
        raise RuntimeError(f"unexpected artifact schema versions: {sorted(schema_versions)}")
    if file_names != EXPECTED_ARTIFACT_FILE_NAMES:
        raise RuntimeError(f"unexpected artifact file names: {sorted(file_names)}")


async def ensure_bucket_exists(
    *,
    client: Minio,
    config: PersistenceSmokeConfig,
) -> None:
    bucket_exists = await asyncio.to_thread(client.bucket_exists, config.object_store_bucket)
    if bucket_exists:
        return
    if not config.should_create_bucket:
        raise RuntimeError(
            f"object store bucket {config.object_store_bucket} does not exist; "
            "set VALIDATION_SMOKE_CREATE_BUCKET=true to create it"
        )

    await asyncio.to_thread(client.make_bucket, config.object_store_bucket)


async def count_ledger_rows(
    *,
    session_factory: AsyncSessionFactory,
    task_id: str,
) -> LedgerCounts:
    async with session_factory() as session:
        task_count = await session.scalar(
            select(func.count()).select_from(task_runs_table).where(task_runs_table.c.task_id == task_id)
        )
        artifact_count = await session.scalar(
            select(func.count()).select_from(task_artifacts_table).where(task_artifacts_table.c.task_id == task_id)
        )

    return LedgerCounts(
        task_count=int(task_count or 0),
        artifact_count=int(artifact_count or 0),
    )


def validate_ledger_counts(
    *,
    counts: LedgerCounts,
    expected_artifact_count: int,
) -> None:
    if counts.task_count != 1:
        raise RuntimeError(f"expected 1 task_run row, got {counts.task_count}")
    if counts.artifact_count != expected_artifact_count:
        raise RuntimeError(f"expected {expected_artifact_count} task_artifact rows, got {counts.artifact_count}")


async def validate_object_store_objects(
    *,
    client: Minio,
    manifest: FactorValidationManifest,
) -> None:
    for artifact in manifest.artifacts:
        if artifact.bucket_name is None or artifact.object_key is None:
            raise RuntimeError(f"artifact {artifact.artifact_id} is missing object storage location")

        object_stat = await asyncio.to_thread(
            client.stat_object,
            artifact.bucket_name,
            artifact.object_key,
        )
        expected_size = artifact.file_size_bytes
        actual_size = getattr(object_stat, "size", None)
        if expected_size != actual_size:
            raise RuntimeError(
                f"object size mismatch for {artifact.object_key}: expected {expected_size}, got {actual_size}"
            )


def read_config_from_env(*, env: Mapping[str, str]) -> PersistenceSmokeConfig:
    missing_keys = [
        key
        for key in (
            "VALIDATION_DATABASE_URL",
            "VALIDATION_OBJECT_STORE_ENDPOINT",
            "VALIDATION_OBJECT_STORE_ACCESS_KEY",
            "VALIDATION_OBJECT_STORE_SECRET_KEY",
        )
        if not _read_required_env(env=env, key=key)
    ]
    if missing_keys:
        raise RuntimeError(f"missing required environment variables: {', '.join(missing_keys)}")

    return PersistenceSmokeConfig(
        database_url=_read_required_env(env=env, key="VALIDATION_DATABASE_URL"),
        object_store_endpoint=_read_required_env(env=env, key="VALIDATION_OBJECT_STORE_ENDPOINT"),
        object_store_access_key=_read_required_env(env=env, key="VALIDATION_OBJECT_STORE_ACCESS_KEY"),
        object_store_secret_key=_read_required_env(env=env, key="VALIDATION_OBJECT_STORE_SECRET_KEY"),
        object_store_bucket=_read_optional_env(
            env=env,
            key="VALIDATION_OBJECT_STORE_BUCKET",
            default=DEFAULT_BUCKET_NAME,
        ),
        object_store_secure=parse_bool(
            value=env.get("VALIDATION_OBJECT_STORE_SECURE"),
            default=False,
        ),
        should_create_schema=parse_bool(
            value=env.get("VALIDATION_SMOKE_CREATE_SCHEMA"),
            default=True,
        ),
        should_create_bucket=parse_bool(
            value=env.get("VALIDATION_SMOKE_CREATE_BUCKET"),
            default=False,
        ),
        run_id=_read_optional_env(
            env=env,
            key="VALIDATION_SMOKE_RUN_ID",
            default=DEFAULT_RUN_ID,
        ),
    )


def parse_bool(*, value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default

    normalized_value = value.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        return False

    raise RuntimeError(f"invalid boolean value: {value}")


def load_dotenv_file(*, env_file_path: str = ".env") -> None:
    if not os.path.exists(env_file_path):
        return

    with open(env_file_path, encoding="utf-8") as env_file:
        for raw_line in env_file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


def _read_required_env(*, env: Mapping[str, str], key: str) -> str:
    value = env.get(key, "").strip()
    if value:
        return value
    return ""


def _read_optional_env(*, env: Mapping[str, str], key: str, default: str) -> str:
    value = env.get(key, "").strip()
    if value:
        return value
    return default


def main() -> int:
    load_dotenv_file()
    try:
        config = read_config_from_env(env=os.environ)
        results = asyncio.run(run_persistence_smoke(config=config))
    except Exception as error:
        print(f"persistence smoke failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
