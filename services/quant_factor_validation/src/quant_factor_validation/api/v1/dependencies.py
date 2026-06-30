from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from quant_factor_validation.core.config import get_settings
from quant_factor_validation.integrations import MinioValidationArtifactStore, create_minio_client
from quant_factor_validation.repositories.market_data_reader import QuantDataHubMarketDataReader
from quant_factor_validation.repositories.validation_ledger import (
    SqlAlchemyValidationLedgerRepository,
    create_validation_database_engine,
    create_validation_session_factory,
)
from quant_factor_validation.services.factor_validation_service import FactorValidationService
from quant_factor_validation.services.validation_persistence import (
    ValidationArtifactStore,
    ValidationLedgerRepository,
    ValidationPersistenceService,
)


@lru_cache
def get_market_data_reader() -> QuantDataHubMarketDataReader:
    settings = get_settings()
    return QuantDataHubMarketDataReader(
        base_url=settings.quant_data_hub_base_url,
        api_token=settings.quant_data_api_token,
        timeout=settings.quant_data_hub_timeout_seconds,
    )


def get_factor_validation_service() -> FactorValidationService:
    return FactorValidationService(
        market_data_reader=get_market_data_reader(),
        persistence_service=get_validation_persistence_service(),
    )


@lru_cache
def get_validation_persistence_service() -> ValidationPersistenceService:
    settings = get_settings()
    if not settings.validation_persistence_enabled:
        return ValidationPersistenceService.disabled()

    return ValidationPersistenceService(
        is_enabled=True,
        artifact_store=get_validation_artifact_store(),
        ledger_repository=get_validation_ledger_repository(),
    )


@lru_cache
def get_validation_database_engine() -> AsyncEngine | None:
    settings = get_settings()
    if not settings.validation_persistence_enabled:
        return None
    if not settings.validation_database_url:
        return None

    return create_validation_database_engine(
        database_url=settings.validation_database_url,
        echo=settings.validation_database_echo,
        schema_name=settings.validation_database_schema,
    )


@lru_cache
def get_validation_session_factory() -> async_sessionmaker[AsyncSession] | None:
    engine = get_validation_database_engine()
    if engine is None:
        return None

    return create_validation_session_factory(engine=engine)


@lru_cache
def get_validation_ledger_repository() -> ValidationLedgerRepository | None:
    session_factory = get_validation_session_factory()
    if session_factory is None:
        return None

    return SqlAlchemyValidationLedgerRepository(session_factory=session_factory)


@lru_cache
def get_validation_artifact_store() -> ValidationArtifactStore | None:
    settings = get_settings()
    if not settings.validation_persistence_enabled:
        return None
    if not settings.validation_object_store_endpoint:
        return None
    if not settings.validation_object_store_access_key:
        return None
    if not settings.validation_object_store_secret_key:
        return None

    return MinioValidationArtifactStore(
        client=create_minio_client(
            endpoint=settings.validation_object_store_endpoint,
            access_key=settings.validation_object_store_access_key,
            secret_key=settings.validation_object_store_secret_key,
            secure=settings.validation_object_store_secure,
        ),
        bucket_name=settings.validation_object_store_bucket,
    )


async def close_validation_database_engine() -> None:
    engine = get_validation_database_engine()
    if engine is not None:
        await engine.dispose()

    get_validation_persistence_service.cache_clear()
    get_validation_database_engine.cache_clear()
    get_validation_session_factory.cache_clear()
    get_validation_ledger_repository.cache_clear()


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_market_data_reader.cache_clear()
    get_validation_persistence_service.cache_clear()
    get_validation_database_engine.cache_clear()
    get_validation_session_factory.cache_clear()
    get_validation_ledger_repository.cache_clear()
    get_validation_artifact_store.cache_clear()
