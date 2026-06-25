from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from quant_ops_api.api.v1.dependencies import get_overview_service
from quant_ops_api.main import create_app
from quant_ops_api.schemas import OpsOverviewResponse, ServiceHealth


class FakeOverviewService:
    async def get_overview(self) -> OpsOverviewResponse:
        return OpsOverviewResponse(
            status="ok",
            generated_at=datetime.now(timezone.utc),
            services=[
                ServiceHealth(
                    name="quant_data_hub",
                    base_url="http://quant_data_hub:8000",
                    status="ok",
                    checked_at=datetime.now(timezone.utc),
                )
            ],
            service_count=1,
            healthy_count=1,
            degraded_count=0,
            down_count=0,
        )


class OverviewRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_overview_service] = lambda: FakeOverviewService()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_return_service_overview_when_called(self) -> None:
        response = self.client.get("/api/v1/overview")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["service_count"], 1)
        self.assertEqual(payload["services"][0]["name"], "quant_data_hub")


if __name__ == "__main__":
    unittest.main()
