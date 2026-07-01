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
        self.assertEqual(payload["meta"]["algorithm_id"], "technical.momentum")
        self.assertEqual(payload["meta"]["row_count"], 3)
        self.assertEqual(payload["rows"][2]["factor_value"], "0.5")

    def test_should_list_algorithm_specs(self) -> None:
        response = self.client.get("/api/v1/algorithms")
        payload = response.json()

        algorithm_ids = [item["algorithm_id"] for item in payload]

        self.assertEqual(response.status_code, 200)
        self.assertIn("technical.momentum", algorithm_ids)
        self.assertIn("volatility.egarch", algorithm_ids)

    def test_should_preview_algorithm_review_gate_evidence_when_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/algorithms/review-gates/evidence/preview",
            json={
                "algorithm_id": "volatility.egarch",
                "gate_id": "validation_evidence",
                "submitted_by": "researcher_a",
                "evidence_type": "validation_report",
                "evidence_source": "factor_validation/egarch_20d/comparison_report.json",
                "summary": "Rank IC, IC decay, and turnover evidence for EGARCH.",
                "artifact_id": "egarch_20d_comparison_report",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["persistence_status"], "not_persisted")
        self.assertEqual(payload["record"]["algorithm_id"], "volatility.egarch")
        self.assertEqual(payload["record"]["gate_id"], "validation_evidence")
        self.assertEqual(payload["record"]["previous_gate_status"], "missing")
        self.assertEqual(payload["record"]["evidence_status"], "submitted")

    def test_should_return_not_found_when_review_gate_is_unknown(self) -> None:
        response = self.client.post(
            "/api/v1/algorithms/review-gates/evidence/preview",
            json={
                "algorithm_id": "volatility.egarch",
                "gate_id": "unknown_gate",
                "submitted_by": "researcher_a",
                "evidence_type": "validation_report",
                "evidence_source": "factor_validation/egarch_20d/comparison_report.json",
                "summary": "Evidence for an unknown gate.",
            },
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("review gate not found", response.json()["detail"])

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
