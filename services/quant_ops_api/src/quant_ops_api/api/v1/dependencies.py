from functools import lru_cache

from quant_ops_api.clients import ServiceHealthClient
from quant_ops_api.core.config import get_settings
from quant_ops_api.services import OverviewService


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


def reset_dependencies() -> None:
    get_settings.cache_clear()
    get_service_health_client.cache_clear()
