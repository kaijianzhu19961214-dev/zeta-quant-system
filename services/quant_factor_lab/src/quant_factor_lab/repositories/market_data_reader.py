from typing import Protocol

from quant_contracts import MarketBarsQuery, MarketBarsResponse
from quant_data_sdk import AsyncQuantDataClient


class MarketDataReader(Protocol):
    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        """Read market bars from a standard market data source."""


class QuantDataHubMarketDataReader:
    def __init__(
        self,
        *,
        base_url: str,
        api_token: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        self.base_url = base_url
        self.api_token = api_token
        self.timeout = timeout

    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        async with AsyncQuantDataClient(
            base_url=self.base_url,
            api_token=self.api_token,
            timeout=self.timeout,
        ) as client:
            return await client.market.query_bars(query=query)
