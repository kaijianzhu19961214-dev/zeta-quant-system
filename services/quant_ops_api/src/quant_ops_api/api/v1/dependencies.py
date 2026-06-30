from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine

from quant_ops_api.clients import ServiceHealthClient
from quant_ops_api.core.config import get_settings
from quant_ops_api.repositories import SqlAlchemyValidationLedgerReader, create_validation_ledger_reader_engine
from quant_ops_api.services import ArtifactLedgerService, FactorValidationReviewService, OverviewService


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


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_service_health_client.cache_clear()
    get_validation_ledger_engine.cache_clear()
