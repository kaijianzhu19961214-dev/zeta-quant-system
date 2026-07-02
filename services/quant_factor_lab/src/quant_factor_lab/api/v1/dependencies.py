from functools import lru_cache

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from quant_factor_lab.core.config import get_settings
from quant_factor_lab.repositories.algorithm_review_evidence import (
    SqlAlchemyAlgorithmReviewEvidenceRepository,
    create_algorithm_review_database_engine,
    create_algorithm_review_evidence_schema,
    create_algorithm_review_session_factory,
)
from quant_factor_lab.repositories.market_data_reader import QuantDataHubMarketDataReader
from quant_factor_lab.services.algorithm_review_service import AlgorithmReviewEvidenceRepository, AlgorithmReviewService
from quant_factor_lab.services.factor_calculation_service import FactorCalculationService


@lru_cache
def get_market_data_reader() -> QuantDataHubMarketDataReader:
    settings = get_settings()
    return QuantDataHubMarketDataReader(
        base_url=settings.quant_data_hub_base_url,
        api_token=settings.quant_data_api_token,
        timeout=settings.quant_data_hub_timeout_seconds,
    )


def get_factor_calculation_service() -> FactorCalculationService:
    return FactorCalculationService(market_data_reader=get_market_data_reader())


def get_algorithm_review_service() -> AlgorithmReviewService:
    return AlgorithmReviewService(evidence_repository=get_algorithm_review_evidence_repository())


@lru_cache
def get_algorithm_review_database_engine() -> AsyncEngine | None:
    settings = get_settings()
    if not settings.algorithm_review_persistence_enabled:
        return None
    if not settings.algorithm_review_database_url:
        return None

    return create_algorithm_review_database_engine(
        database_url=settings.algorithm_review_database_url,
        echo=settings.algorithm_review_database_echo,
        schema_name=settings.algorithm_review_database_schema,
    )


@lru_cache
def get_algorithm_review_session_factory() -> async_sessionmaker[AsyncSession] | None:
    engine = get_algorithm_review_database_engine()
    if engine is None:
        return None

    return create_algorithm_review_session_factory(engine=engine)


@lru_cache
def get_algorithm_review_evidence_repository() -> AlgorithmReviewEvidenceRepository | None:
    session_factory = get_algorithm_review_session_factory()
    if session_factory is None:
        return None

    return SqlAlchemyAlgorithmReviewEvidenceRepository(session_factory=session_factory)


async def initialize_algorithm_review_storage() -> None:
    settings = get_settings()
    if not settings.algorithm_review_persistence_enabled:
        return
    if not settings.algorithm_review_create_schema:
        return

    engine = get_algorithm_review_database_engine()
    if engine is None:
        return

    await create_algorithm_review_evidence_schema(
        engine=engine,
        schema_name=settings.algorithm_review_database_schema,
    )


async def close_algorithm_review_database_engine() -> None:
    engine = get_algorithm_review_database_engine()
    if engine is not None:
        await engine.dispose()

    get_algorithm_review_database_engine.cache_clear()
    get_algorithm_review_session_factory.cache_clear()
    get_algorithm_review_evidence_repository.cache_clear()


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_market_data_reader.cache_clear()
    get_algorithm_review_database_engine.cache_clear()
    get_algorithm_review_session_factory.cache_clear()
    get_algorithm_review_evidence_repository.cache_clear()
