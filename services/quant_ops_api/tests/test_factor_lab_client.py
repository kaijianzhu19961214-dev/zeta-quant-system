import unittest

import httpx

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


if __name__ == "__main__":
    unittest.main()
