from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine

from quant_ops_api.clients import FactorLabClient, FactorValidationClient, ServiceHealthClient
from quant_ops_api.core.config import get_settings
from quant_ops_api.integrations import MinioArtifactObjectReader, create_minio_client
from quant_ops_api.repositories import SqlAlchemyValidationLedgerReader, create_validation_ledger_reader_engine
from quant_ops_api.services import (
    ArtifactLedgerService,
    FactorComparisonArtifactService,
    FactorValidationReviewService,
    OverviewService,
)


@lru_cache
def get_service_health_client() -> ServiceHealthClient:
    settings = get_settings()
    return ServiceHealthClient(timeout_seconds=settings.service_health_timeout_seconds)


def get_overview_service() -> OverviewService:
    settings = get_settings()
    return OverviewService(
        endpoints=settings.service_endpoints(),
        health_client=get_service_health_client(),
    )


def get_factor_validation_review_service() -> FactorValidationReviewService:
    return FactorValidationReviewService()


@lru_cache
def get_factor_validation_client() -> FactorValidationClient:
    settings = get_settings()
    return FactorValidationClient(
        base_url=settings.quant_factor_validation_base_url,
        timeout_seconds=settings.service_health_timeout_seconds,
    )


@lru_cache
def get_factor_lab_client() -> FactorLabClient:
    settings = get_settings()
    return FactorLabClient(
        base_url=settings.quant_factor_lab_base_url,
        timeout_seconds=settings.service_health_timeout_seconds,
    )


@lru_cache
def get_validation_ledger_engine() -> AsyncEngine | None:
    settings = get_settings()
    database_url = settings.artifact_ledger_read_database_url()
    if database_url is None:
        return None
    return create_validation_ledger_reader_engine(
        database_url=database_url,
        schema_name=settings.artifact_ledger_read_database_schema(),
    )


def get_validation_ledger_reader() -> SqlAlchemyValidationLedgerReader | None:
    engine = get_validation_ledger_engine()
    if engine is None:
        return None
    return SqlAlchemyValidationLedgerReader(engine=engine)


async def dispose_validation_ledger_engine() -> None:
    if get_validation_ledger_engine.cache_info().currsize == 0:
        return

    engine = get_validation_ledger_engine()
    if engine is not None:
        await engine.dispose()
    get_validation_ledger_engine.cache_clear()


def get_artifact_ledger_service() -> ArtifactLedgerService:
    settings = get_settings()
    return ArtifactLedgerService(
        validation_review_service=get_factor_validation_review_service(),
        validation_ledger_reader=get_validation_ledger_reader(),
        query_limit=settings.artifact_ledger_query_limit,
    )


@lru_cache
def get_artifact_object_reader() -> MinioArtifactObjectReader | None:
    settings = get_settings()
    endpoint = settings.artifact_object_store_read_endpoint()
    access_key = settings.artifact_object_store_read_access_key()
    secret_key = settings.artifact_object_store_read_secret_key()
    if endpoint is None or access_key is None or secret_key is None:
        return None

    return MinioArtifactObjectReader(
        client=create_minio_client(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=settings.artifact_object_store_read_secure(),
        )
    )


def get_factor_comparison_artifact_service() -> FactorComparisonArtifactService:
    return FactorComparisonArtifactService(object_reader=get_artifact_object_reader())


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_service_health_client.cache_clear()
    get_factor_lab_client.cache_clear()
    get_factor_validation_client.cache_clear()
    get_validation_ledger_engine.cache_clear()
    get_artifact_object_reader.cache_clear()
