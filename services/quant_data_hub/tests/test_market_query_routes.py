import unittest

from fastapi.testclient import TestClient
from quant_contracts import MarketBarsMeta, MarketBarsResponse, PriceMode, Timeframe

from quant_data_hub.api.v1.dependencies import get_market_query_service
from quant_data_hub.main import create_app


class FakeMarketQueryService:
    async def query_bars(self, request):
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                dataset_code=request.dataset_code or "a_share_1d",
                batch_id=request.batch_id,
                row_count=0,
            ),
            rows=[],
        )


class MarketQueryRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_market_query_service] = lambda: FakeMarketQueryService()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_query_market_bars_when_standard_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/market-bars/query",
            json={
                "timeframe": Timeframe.DAY_1,
                "symbols": ["000001.SZ"],
                "start": "2026-01-05",
                "end": "2026-03-13",
                "price_mode": PriceMode.RAW,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["dataset_code"], "a_share_1d")
        self.assertEqual(response.json()["rows"], [])

    def test_should_query_market_bars_when_legacy_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/market/bars/query",
            json={
                "timeframe": "1d",
                "codes": ["000001.SZ"],
                "start": "2026-01-05",
                "end": "2026-03-13",
                "price_mode": "raw",
                "fields": ["code", "date", "close", "vol"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["meta"]["price_mode"], "raw")

    def test_should_return_validation_error_when_qfq_batch_id_is_missing(self) -> None:
        response = self.client.post(
            "/api/v1/market-bars/query",
            json={
                "timeframe": "1d",
                "symbols": ["000001.SZ"],
                "start": "2026-01-05",
                "end": "2026-03-13",
                "price_mode": "qfq",
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()

