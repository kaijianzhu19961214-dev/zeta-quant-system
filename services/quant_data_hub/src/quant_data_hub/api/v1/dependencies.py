from quant_data_hub.core.config import get_settings
from quant_data_hub.integrations.clickhouse import (
    ClickHouseConnectionSettings,
    ClickHouseHttpClient,
)
from quant_data_hub.services.market_query_service import MarketQueryService


def get_market_query_service() -> MarketQueryService:
    settings = get_settings()
    reader = ClickHouseHttpClient(
        ClickHouseConnectionSettings(
            http_url=settings.clickhouse_http_url,
            database=settings.clickhouse_database,
            user=settings.clickhouse_user,
            password=settings.clickhouse_password,
        )
    )
    return MarketQueryService(reader=reader, database=settings.clickhouse_database)

