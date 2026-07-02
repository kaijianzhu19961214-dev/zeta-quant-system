import unittest

from fastapi.testclient import TestClient
from quant_contracts import (
    AlgorithmCapability,
    AlgorithmGatePromotionFinding,
    AlgorithmPromotionReadinessResponse,
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceRecord,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceResponse,
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

    async def review_algorithm_review_gate_evidence(
        self,
        *,
        evidence_id: str,
        request: AlgorithmReviewGateEvidenceReviewRequest,
    ) -> AlgorithmReviewGateEvidenceResponse:
        return AlgorithmReviewGateEvidenceResponse(
            record=AlgorithmReviewGateEvidenceRecord(
                evidence_id=evidence_id,
                algorithm_id="technical.momentum",
                gate_id="validation_evidence",
                gate_category="validation",
                gate_title="Validation evidence",
                previous_gate_status="satisfied",
                submitted_by="codex_smoke",
                evidence_type="validation_report",
                evidence_source="factor_validation/momentum_1d/comparison_report.json",
                summary="Momentum validation smoke evidence from 101 data.",
                submitted_at="2026-07-02T09:30:00+00:00",
                evidence_status=request.evidence_status,
                reviewed_by=request.reviewed_by,
                reviewed_at="2026-07-02T10:30:00+00:00",
                review_comment=request.review_comment,
            ),
            persistence_status="persisted",
        )

    async def get_algorithm_promotion_readiness(
        self,
        *,
        algorithm_id: str,
        limit: int = 200,
    ) -> AlgorithmPromotionReadinessResponse:
        return AlgorithmPromotionReadinessResponse(
            algorithm_id=algorithm_id,
            current_status="available",
            decision="promotable",
            can_promote=True,
            required_gate_count=6,
            met_required_gate_count=6,
            missing_required_gate_ids=[],
            rejected_required_gate_ids=[],
            findings=[
                AlgorithmGatePromotionFinding(
                    gate_id="validation_evidence",
                    gate_title="Validation evidence",
                    gate_status="satisfied",
                    decision="met_by_registry",
                    is_required=True,
                    is_met=True,
                    accepted_evidence_count=1,
                    latest_evidence_status="accepted",
                    message="Registry review gate is already marked satisfied.",
                )
            ],
            generated_at="2026-07-02T10:30:00+00:00",
            limitations=[
                "Promotion readiness is a read-only evaluation; it does not mutate AlgorithmSpec.status.",
            ],
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

    def test_should_review_algorithm_review_gate_evidence_when_called(self) -> None:
        response = self.client.post(
            "/api/v1/factor-lab/algorithms/review-gates/evidence/algorithm_gate_evidence_abc123/review",
            json={
                "reviewed_by": "researcher_lead",
                "evidence_status": "accepted",
                "review_comment": "Evidence accepted.",
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["persistence_status"], "persisted")
        self.assertEqual(payload["record"]["evidence_status"], "accepted")
        self.assertEqual(payload["record"]["reviewed_by"], "researcher_lead")

    def test_should_return_algorithm_promotion_readiness_when_called(self) -> None:
        response = self.client.get("/api/v1/factor-lab/algorithms/technical.momentum/promotion/readiness")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["algorithm_id"], "technical.momentum")
        self.assertEqual(payload["decision"], "promotable")
        self.assertTrue(payload["can_promote"])
        self.assertEqual(payload["required_gate_count"], 6)
        self.assertEqual(payload["findings"][0]["decision"], "met_by_registry")


if __name__ == "__main__":
    unittest.main()
