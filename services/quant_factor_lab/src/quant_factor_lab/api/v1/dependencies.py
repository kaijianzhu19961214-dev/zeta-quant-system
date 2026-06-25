from functools import lru_cache

from quant_factor_lab.core.config import get_settings
from quant_factor_lab.repositories.market_data_reader import QuantDataHubMarketDataReader
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


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_market_data_reader.cache_clear()
