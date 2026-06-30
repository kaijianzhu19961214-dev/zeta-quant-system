import unittest

import httpx

from quant_ops_api.clients import FactorValidationClient, FactorValidationClientError
from quant_ops_api.schemas import ExternalPayloadComparisonRequest, ExternalMetricPayload


class FactorValidationClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_parse_external_payload_comparison_report(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-factor-validation/api/v1/factors/external-payloads/compare",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "factor_name": "momentum_20d",
                    "primary_engine": "alphalens",
                    "engine_results": [],
                    "engine_count": 2,
                    "has_engine_disagreement": False,
                    "comparison_summary": "Evaluation engines agree on the current review decision.",
                },
            )

        client = FactorValidationClient(
            base_url="http://quant-factor-validation",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        report = await client.compare_external_payloads(
            request=ExternalPayloadComparisonRequest(
                factor_name="momentum_20d",
                alphalens_payloads=[
                    ExternalMetricPayload(
                        factor_name="momentum_20d",
                        start_date="2026-01-01",
                        end_date="2026-03-13",
                        forward_days=5,
                        sample_count=180,
                        effective_sample_count=170,
                        metric_values={"mean_ic": 0.035},
                    )
                ],
            )
        )

        self.assertEqual(report.factor_name, "momentum_20d")
        self.assertEqual(report.primary_engine, "alphalens")
        self.assertEqual(report.engine_count, 2)

    async def test_should_raise_client_error_when_comparison_is_rejected(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=422,
                json={"detail": "primary_engine must have at least one matching payload"},
            )

        client = FactorValidationClient(
            base_url="http://quant-factor-validation",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(FactorValidationClientError) as context:
            await client.compare_external_payloads(
                request=ExternalPayloadComparisonRequest(
                    factor_name="momentum_20d",
                    primary_engine="vectorbt",
                    alphalens_payloads=[
                        ExternalMetricPayload(
                            factor_name="momentum_20d",
                            start_date="2026-01-01",
                            end_date="2026-03-13",
                            forward_days=5,
                            sample_count=10,
                            effective_sample_count=8,
                        )
                    ],
                )
            )

        self.assertEqual(context.exception.status_code, 422)
        self.assertEqual(context.exception.message, "primary_engine must have at least one matching payload")


if __name__ == "__main__":
    unittest.main()
