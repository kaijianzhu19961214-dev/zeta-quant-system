from functools import lru_cache

from quant_factor_validation.core.config import get_settings
from quant_factor_validation.integrations import MinioValidationArtifactStore, create_minio_client
from quant_factor_validation.repositories.market_data_reader import QuantDataHubMarketDataReader
from quant_factor_validation.services.factor_validation_service import FactorValidationService
from quant_factor_validation.services.validation_persistence import (
    ValidationArtifactStore,
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
        ledger_repository=None,
    )


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


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_market_data_reader.cache_clear()
    get_validation_persistence_service.cache_clear()
    get_validation_artifact_store.cache_clear()
