import unittest

from fastapi.testclient import TestClient
from quant_contracts import (
    AlgorithmCapability,
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceRecord,
    AlgorithmSpec,
    AssetClass,
    FactorFamily,
    FactorMode,
    Timeframe,
)

from quant_ops_api.api.v1.dependencies import get_factor_lab_client
from quant_ops_api.main import create_app


class FakeFactorLabClient:
    async def list_algorithms(self) -> list[AlgorithmSpec]:
        return [
            AlgorithmSpec(
                algorithm_id="technical.momentum",
                display_name="Momentum return factor",
                status="available",
                description="Calculates close-to-close momentum.",
                capability=AlgorithmCapability(
                    asset_classes=[AssetClass.EQUITY],
                    factor_modes=[FactorMode.CROSS_SECTIONAL],
                    factor_families=[FactorFamily.PRICE_VOLUME],
                    timeframes=[Timeframe.DAY_1],
                    output_kinds=["factor_values"],
                ),
                tags=["momentum"],
            )
        ]

    async def list_algorithm_review_gate_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> AlgorithmReviewGateEvidenceListResponse:
        return AlgorithmReviewGateEvidenceListResponse(
            algorithm_id=algorithm_id,
            gate_id=gate_id,
            records=[
                AlgorithmReviewGateEvidenceRecord(
                    evidence_id="algorithm_gate_evidence_abc123",
                    algorithm_id=algorithm_id,
                    gate_id=gate_id or "validation_evidence",
                    gate_category="validation",
                    gate_title="Validation evidence",
                    previous_gate_status="satisfied",
                    submitted_by="codex_smoke",
                    evidence_type="validation_report",
                    evidence_source="factor_validation/momentum_1d/comparison_report.json",
                    summary="Momentum validation smoke evidence from 101 data.",
                    submitted_at="2026-07-02T09:30:00+00:00",
                )
            ],
            total_count=1,
            persistence_status="persisted",
        )


class FactorLabRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_factor_lab_client] = lambda: FakeFactorLabClient()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_return_algorithm_specs_when_called(self) -> None:
        response = self.client.get("/api/v1/factor-lab/algorithms")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload[0]["algorithm_id"], "technical.momentum")
        self.assertEqual(payload[0]["status"], "available")
        self.assertEqual(payload[0]["capability"]["output_kinds"], ["factor_values"])

    def test_should_return_algorithm_review_gate_evidence_when_called(self) -> None:
        response = self.client.get(
            "/api/v1/factor-lab/algorithms/technical.momentum/review-gates/evidence?gate_id=validation_evidence"
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["algorithm_id"], "technical.momentum")
        self.assertEqual(payload["gate_id"], "validation_evidence")
        self.assertEqual(payload["persistence_status"], "persisted")
        self.assertEqual(payload["records"][0]["evidence_id"], "algorithm_gate_evidence_abc123")


if __name__ == "__main__":
    unittest.main()
