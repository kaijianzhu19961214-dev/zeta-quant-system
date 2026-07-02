import unittest

from fastapi.testclient import TestClient
from quant_contracts import AlgorithmReviewGateEvidenceRecord, MarketBar, MarketBarsMeta, MarketBarsResponse

from quant_factor_lab.api.v1.dependencies import get_algorithm_review_service, get_factor_calculation_service
from quant_factor_lab.main import create_app
from quant_factor_lab.services.algorithm_review_service import AlgorithmReviewService
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


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.records: list[AlgorithmReviewGateEvidenceRecord] = []

    async def record_evidence(
        self,
        *,
        record: AlgorithmReviewGateEvidenceRecord,
    ) -> AlgorithmReviewGateEvidenceRecord:
        self.records.append(record)
        return record

    async def list_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> list[AlgorithmReviewGateEvidenceRecord]:
        records = [record for record in self.records if record.algorithm_id == algorithm_id]
        if gate_id is not None:
            records = [record for record in records if record.gate_id == gate_id]
        return records[:limit]


class FactorCalculationRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.evidence_repository = FakeEvidenceRepository()
        self.app.dependency_overrides[get_factor_calculation_service] = lambda: FactorCalculationService(
            market_data_reader=FakeMarketDataReader()
        )
        self.app.dependency_overrides[get_algorithm_review_service] = lambda: AlgorithmReviewService(
            evidence_repository=self.evidence_repository,
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

    def test_should_submit_algorithm_review_gate_evidence_when_payload_is_valid(self) -> None:
        response = self.client.post(
            "/api/v1/algorithms/review-gates/evidence",
            json={
                "algorithm_id": "technical.momentum",
                "gate_id": "validation_evidence",
                "submitted_by": "codex_smoke",
                "evidence_type": "validation_report",
                "evidence_source": "factor_validation/momentum_1d/comparison_report.json",
                "summary": "Momentum validation smoke evidence from 101 data.",
                "artifact_id": "comparison_report_momentum_1d",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["persistence_status"], "persisted")
        self.assertEqual(payload["record"]["algorithm_id"], "technical.momentum")
        self.assertEqual(payload["record"]["gate_id"], "validation_evidence")
        self.assertEqual(len(self.evidence_repository.records), 1)

    def test_should_list_algorithm_review_gate_evidence_when_records_exist(self) -> None:
        self.client.post(
            "/api/v1/algorithms/review-gates/evidence",
            json={
                "algorithm_id": "technical.momentum",
                "gate_id": "validation_evidence",
                "submitted_by": "codex_smoke",
                "evidence_type": "validation_report",
                "evidence_source": "factor_validation/momentum_1d/comparison_report.json",
                "summary": "Momentum validation smoke evidence from 101 data.",
            },
        )

        response = self.client.get(
            "/api/v1/algorithms/technical.momentum/review-gates/evidence?gate_id=validation_evidence"
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["persistence_status"], "persisted")
        self.assertEqual(payload["total_count"], 1)
        self.assertEqual(payload["records"][0]["gate_id"], "validation_evidence")

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
