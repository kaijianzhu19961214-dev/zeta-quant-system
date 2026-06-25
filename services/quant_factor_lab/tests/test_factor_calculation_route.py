import unittest

from fastapi.testclient import TestClient
from quant_contracts import MarketBar, MarketBarsMeta, MarketBarsResponse

from quant_factor_lab.api.v1.dependencies import get_factor_calculation_service
from quant_factor_lab.main import create_app
from quant_factor_lab.services.factor_calculation_service import FactorCalculationService


class FakeMarketDataReader:
    async def query_bars(self, *, query):
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=query.timeframe,
                price_mode=query.price_mode,
                row_count=3,
                dataset_code="a_share_1d",
                batch_id=query.batch_id,
            ),
            rows=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-11", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-12", close_price="11"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="15"),
            ],
        )


class FactorCalculationRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_factor_calculation_service] = lambda: FactorCalculationService(
            market_data_reader=FakeMarketDataReader()
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_calculate_factor_when_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/factors/calculate",
            json={
                "factor_name": "momentum_2d",
                "symbols": ["000001.SZ"],
                "start": "2026-03-11",
                "end": "2026-03-13",
                "lookback_window": 2,
                "run_id": "run_route_test",
            },
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["meta"]["factor_name"], "momentum_2d")
        self.assertEqual(payload["meta"]["row_count"], 3)
        self.assertEqual(payload["rows"][2]["factor_value"], "0.5")

    def test_should_return_validation_error_when_factor_is_not_supported(self) -> None:
        response = self.client.post(
            "/api/v1/factors/calculate",
            json={
                "factor_name": "volatility_20d",
                "symbols": ["000001.SZ"],
                "start": "2026-03-11",
                "end": "2026-03-13",
                "lookback_window": 20,
            },
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
