from datetime import date
import unittest

from quant_contracts import (
    MarketBar,
    MarketBarsMeta,
    MarketBarsQuery,
    MarketBarsResponse,
    PriceMode,
    Timeframe,
)

from quant_ops_api.schemas import MarketDataBarsSampleRequest, QfqBatchSummary
from quant_ops_api.services.market_data_service import MarketDataService


class FakeQuantDataHubClient:
    def __init__(self) -> None:
        self.market_query: MarketBarsQuery | None = None

    async def list_qfq_batches(self, *, limit: int = 20) -> list[QfqBatchSummary]:
        return [
            QfqBatchSummary(
                batch_id="qfq_20260610",
                qfq_base_date=date(2026, 6, 10),
                status="succeeded",
            )
        ]

    async def query_market_bars(self, *, request: MarketBarsQuery) -> MarketBarsResponse:
        self.market_query = request
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                row_count=1,
                dataset_code="a_share_1d",
                batch_id=request.batch_id,
            ),
            rows=[
                MarketBar(
                    symbol=request.symbols[0],
                    trade_date=date(2026, 6, 10),
                    close_price="10.00",
                )
            ],
        )


class MarketDataServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_resolve_latest_qfq_batch_for_sample_query(self) -> None:
        client = FakeQuantDataHubClient()
        service = MarketDataService(quant_data_hub_client=client)
        request = MarketDataBarsSampleRequest(
            symbol="000001.SZ",
            timeframe="1d",
            start="2026-06-10",
            end="2026-06-10",
            price_mode="qfq",
            limit=5,
        )

        response = await service.query_sample_bars(request=request)

        self.assertIsNotNone(client.market_query)
        self.assertEqual(client.market_query.price_mode, PriceMode.QFQ)
        self.assertEqual(client.market_query.timeframe, Timeframe.DAY_1)
        self.assertEqual(client.market_query.batch_id, "qfq_20260610")
        self.assertEqual(response.request.batch_id, "qfq_20260610")
        self.assertEqual(response.meta.batch_id, "qfq_20260610")
        self.assertEqual(response.meta.qfq_base_date, date(2026, 6, 10))


if __name__ == "__main__":
    unittest.main()
