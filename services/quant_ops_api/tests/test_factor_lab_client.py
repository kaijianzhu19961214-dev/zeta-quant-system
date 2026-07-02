import unittest

import httpx
from quant_contracts import AlgorithmReviewGateEvidenceReviewRequest, FactorCalculationRequest

from quant_ops_api.clients import FactorLabClient, FactorLabClientError


class FactorLabClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_parse_algorithm_specs(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://quant-factor-lab/api/v1/algorithms")
            return httpx.Response(
                status_code=200,
                json=[
                    {
                        "algorithm_id": "technical.momentum",
                        "display_name": "Momentum return factor",
                        "role": "factor_generator",
                        "status": "available",
                        "version": "v1",
                        "description": "Calculates close-to-close momentum.",
                        "source_library": None,
                        "source_url": None,
                        "adapter_module": "quant_factor_lab.algorithms.technical.momentum_adapter",
                        "capability": {
                            "asset_classes": ["equity", "futures"],
                            "factor_modes": ["cross_sectional", "time_series"],
                            "factor_families": ["price_volume"],
                            "timeframes": ["1d"],
                            "output_kinds": ["factor_values"],
                        },
                        "parameters": [],
                        "tags": ["momentum"],
                        "research_notes": [],
                        "limitations": [],
                    }
                ],
            )

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        specs = await client.list_algorithms()

        self.assertEqual(specs[0].algorithm_id, "technical.momentum")
        self.assertEqual(specs[0].status, "available")

    async def test_should_raise_client_error_when_payload_is_invalid(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"algorithm_id": "technical.momentum"})

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(FactorLabClientError) as context:
            await client.list_algorithms()

        self.assertEqual(context.exception.status_code, 502)

    async def test_should_parse_algorithm_review_gate_evidence(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-factor-lab/api/v1/algorithms/technical.momentum/review-gates/evidence?limit=20&gate_id=validation_evidence",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "algorithm_id": "technical.momentum",
                    "gate_id": "validation_evidence",
                    "records": [
                        {
                            "evidence_id": "algorithm_gate_evidence_abc123",
                            "algorithm_id": "technical.momentum",
                            "gate_id": "validation_evidence",
                            "gate_category": "validation",
                            "gate_title": "Validation evidence",
                            "previous_gate_status": "satisfied",
                            "submitted_by": "codex_smoke",
                            "evidence_type": "validation_report",
                            "evidence_source": "factor_validation/momentum_1d/comparison_report.json",
                            "summary": "Momentum validation smoke evidence from 101 data.",
                            "submitted_at": "2026-07-02T09:30:00+00:00",
                        }
                    ],
                    "total_count": 1,
                    "persistence_status": "persisted",
                    "limitations": [],
                },
            )

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        response = await client.list_algorithm_review_gate_evidence(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            limit=20,
        )

        self.assertEqual(response.persistence_status, "persisted")
        self.assertEqual(response.total_count, 1)
        self.assertEqual(response.records[0].gate_id, "validation_evidence")

    async def test_should_parse_algorithm_review_gate_evidence_review_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-factor-lab/api/v1/algorithms/review-gates/evidence/algorithm_gate_evidence_abc123/review",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "record": {
                        "evidence_id": "algorithm_gate_evidence_abc123",
                        "algorithm_id": "technical.momentum",
                        "gate_id": "validation_evidence",
                        "gate_category": "validation",
                        "gate_title": "Validation evidence",
                        "previous_gate_status": "satisfied",
                        "submitted_by": "codex_smoke",
                        "evidence_type": "validation_report",
                        "evidence_source": "factor_validation/momentum_1d/comparison_report.json",
                        "summary": "Momentum validation smoke evidence from 101 data.",
                        "submitted_at": "2026-07-02T09:30:00+00:00",
                        "evidence_status": "accepted",
                        "reviewed_by": "researcher_lead",
                        "reviewed_at": "2026-07-02T10:30:00+00:00",
                        "review_comment": "Evidence accepted.",
                    },
                    "persistence_status": "persisted",
                    "limitations": [],
                },
            )

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        response = await client.review_algorithm_review_gate_evidence(
            evidence_id="algorithm_gate_evidence_abc123",
            request=AlgorithmReviewGateEvidenceReviewRequest(
                reviewed_by="researcher_lead",
                evidence_status="accepted",
                review_comment="Evidence accepted.",
            ),
        )

        self.assertEqual(response.persistence_status, "persisted")
        self.assertEqual(response.record.evidence_status, "accepted")
        self.assertEqual(response.record.reviewed_by, "researcher_lead")

    async def test_should_parse_algorithm_promotion_readiness(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-factor-lab/api/v1/algorithms/technical.momentum/promotion/readiness?limit=200",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "algorithm_id": "technical.momentum",
                    "current_status": "available",
                    "decision": "promotable",
                    "can_promote": True,
                    "required_gate_count": 6,
                    "met_required_gate_count": 6,
                    "missing_required_gate_ids": [],
                    "rejected_required_gate_ids": [],
                    "findings": [
                        {
                            "gate_id": "validation_evidence",
                            "gate_title": "Validation evidence",
                            "gate_status": "satisfied",
                            "decision": "met_by_registry",
                            "is_required": True,
                            "is_met": True,
                            "accepted_evidence_count": 1,
                            "latest_evidence_status": "accepted",
                            "message": "Registry review gate is already marked satisfied.",
                        }
                    ],
                    "generated_at": "2026-07-02T10:30:00+00:00",
                    "limitations": [
                        "Promotion readiness is a read-only evaluation; it does not mutate AlgorithmSpec.status.",
                    ],
                },
            )

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        response = await client.get_algorithm_promotion_readiness(algorithm_id="technical.momentum")

        self.assertEqual(response.algorithm_id, "technical.momentum")
        self.assertEqual(response.decision, "promotable")
        self.assertTrue(response.can_promote)
        self.assertEqual(response.findings[0].decision, "met_by_registry")

    async def test_should_parse_factor_calculation_response(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://quant-factor-lab/api/v1/factors/calculate")
            self.assertEqual(request.method, "POST")
            self.assertIn('"factor_name":"momentum_1d"', request.read().decode())
            return httpx.Response(
                status_code=200,
                json={
                    "meta": {
                        "factor_name": "momentum_1d",
                        "algorithm_id": "technical.momentum",
                        "algorithm_version": "v1",
                        "algorithm_source_library": None,
                        "asset_class": "equity",
                        "factor_mode": "cross_sectional",
                        "factor_family": "price_volume",
                        "timeframe": "1d",
                        "price_mode": "raw",
                        "row_count": 2,
                        "lookback_window": 1,
                        "universe_name": "default",
                        "data_source": "quant_data_hub",
                        "data_version": None,
                        "factor_version": "v1",
                        "run_id": "ops_real_sample_momentum_1d",
                        "dataset_code": "a_share_1d",
                        "batch_id": None,
                    },
                    "rows": [
                        {
                            "symbol": "000001.SZ",
                            "trade_date": "2026-06-09",
                            "factor_name": "momentum_1d",
                            "factor_value": None,
                        },
                        {
                            "symbol": "000001.SZ",
                            "trade_date": "2026-06-10",
                            "factor_name": "momentum_1d",
                            "factor_value": "0.017070979335130278526504942",
                        },
                    ],
                },
            )

        client = FactorLabClient(
            base_url="http://quant-factor-lab",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )
        request = FactorCalculationRequest(
            factor_name="momentum_1d",
            symbols=["000001.SZ"],
            start="2026-06-09",
            end="2026-06-10",
            lookback_window=1,
            limit=10,
        )

        response = await client.calculate_factor(request=request)

        self.assertEqual(response.meta.algorithm_id, "technical.momentum")
        self.assertEqual(response.meta.row_count, 2)
        self.assertEqual(str(response.rows[1].factor_value), "0.017070979335130278526504942")


if __name__ == "__main__":
    unittest.main()
