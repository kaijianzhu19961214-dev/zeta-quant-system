import unittest

from fastapi.testclient import TestClient
from quant_contracts import (
    AlgorithmCapability,
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


if __name__ == "__main__":
    unittest.main()
