import unittest

from fastapi.testclient import TestClient
from quant_contracts import MarketBar, MarketBarsMeta, MarketBarsResponse

from quant_factor_validation.api.v1.dependencies import get_factor_validation_service
from quant_factor_validation.main import create_app
from quant_factor_validation.services import FactorValidationService


class FakeMarketDataReader:
    async def query_bars(self, *, query):
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=query.timeframe,
                price_mode=query.price_mode,
                row_count=4,
                dataset_code="a_share_1d",
                batch_id=query.batch_id,
            ),
            rows=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-16", close_price="11"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-16", close_price="12"),
            ],
        )


class FactorValidationRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_factor_validation_service] = lambda: FactorValidationService(
            market_data_reader=FakeMarketDataReader()
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_validate_factor_when_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/factors/validate",
            json={
                "factor_name": "momentum_1d",
                "factor_values": [
                    {
                        "symbol": "000001.SZ",
                        "trade_date": "2026-03-13",
                        "factor_name": "momentum_1d",
                        "factor_value": "0.1",
                    },
                    {
                        "symbol": "000002.SZ",
                        "trade_date": "2026-03-13",
                        "factor_name": "momentum_1d",
                        "factor_value": "0.2",
                    },
                ],
                "market_start": "2026-03-13",
                "market_end": "2026-03-16",
                "forward_days": 1,
                "group_count": 2,
            },
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["metrics"]["factor_name"], "momentum_1d")
        self.assertEqual(payload["metrics"]["effective_sample_count"], 2)
        self.assertEqual(payload["metrics"]["group_count"], 2)
        self.assertEqual(len(payload["group_returns"]), 2)
        self.assertEqual(payload["ic_series"][0]["rank_ic"], 1.0)
        self.assertEqual(payload["report"]["decision"], "review_required")
        self.assertEqual(payload["manifest"]["persistence_status"], "not_persisted")
        self.assertEqual(payload["manifest"]["artifacts"][0]["artifact_type"], "validation_report")

    def test_should_return_validation_error_when_factor_names_mismatch(self) -> None:
        response = self.client.post(
            "/api/v1/factors/validate",
            json={
                "factor_name": "momentum_1d",
                "factor_values": [
                    {
                        "symbol": "000001.SZ",
                        "trade_date": "2026-03-13",
                        "factor_name": "reversal_5d",
                        "factor_value": "0.1",
                    }
                ],
                "market_start": "2026-03-13",
                "market_end": "2026-03-16",
            },
        )

        self.assertEqual(response.status_code, 422)

    def test_should_compare_external_payloads_when_payload_set_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/factors/external-payloads/compare",
            json={
                "factor_name": "momentum_20d",
                "primary_engine": "alphalens",
                "alphalens_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 180,
                        "effective_sample_count": 170,
                        "metric_values": {
                            "mean_ic": 0.035,
                            "rank_ic_mean": 0.06,
                            "ic_std": 0.08,
                            "ic_ir": 0.4375,
                            "mean_return_spread": 0.045,
                        },
                    }
                ],
                "qlib_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 180,
                        "effective_sample_count": 166,
                        "metric_values": {
                            "ic_mean": 0.033,
                            "rank_ic_mean": 0.055,
                            "ic_std": 0.08,
                            "icir": 0.4125,
                            "return_spread": 0.04,
                        },
                    }
                ],
            },
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["factor_name"], "momentum_20d")
        self.assertEqual(payload["primary_engine"], "alphalens")
        self.assertEqual(payload["engine_count"], 2)
        self.assertEqual(
            {result["evaluation_engine"] for result in payload["engine_results"]},
            {"alphalens", "qlib"},
        )

    def test_should_return_validation_error_when_primary_payload_is_missing(self) -> None:
        response = self.client.post(
            "/api/v1/factors/external-payloads/compare",
            json={
                "factor_name": "momentum_20d",
                "primary_engine": "vectorbt",
                "alphalens_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 10,
                        "effective_sample_count": 8,
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "primary_engine must have at least one matching payload")


if __name__ == "__main__":
    unittest.main()
