import unittest

import httpx
from quant_contracts import AlgorithmReviewGateEvidenceReviewRequest

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


if __name__ == "__main__":
    unittest.main()
