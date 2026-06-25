from datetime import datetime, timezone
import unittest

from quant_ops_api.schemas import ServiceEndpoint, ServiceHealth
from quant_ops_api.services.overview_service import OverviewService, build_overview_response


class FakeHealthClient:
    def __init__(self, *, health_by_name: dict[str, ServiceHealth]) -> None:
        self.health_by_name = health_by_name
        self.requested_names: list[str] = []

    async def fetch_health(self, *, endpoint: ServiceEndpoint) -> ServiceHealth:
        self.requested_names.append(endpoint.name)
        return self.health_by_name[endpoint.name]


class OverviewServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_ok_when_all_services_are_healthy(self) -> None:
        service = OverviewService(
            endpoints=[
                ServiceEndpoint(name="quant_data_hub", base_url="http://data"),
                ServiceEndpoint(name="quant_factor_lab", base_url="http://lab"),
            ],
            health_client=FakeHealthClient(
                health_by_name={
                    "quant_data_hub": _make_health(name="quant_data_hub", status="ok"),
                    "quant_factor_lab": _make_health(name="quant_factor_lab", status="ok"),
                }
            ),
        )

        response = await service.get_overview()

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.healthy_count, 2)
        self.assertEqual(response.down_count, 0)

    async def test_should_return_degraded_when_one_service_is_down(self) -> None:
        service = OverviewService(
            endpoints=[
                ServiceEndpoint(name="quant_data_hub", base_url="http://data"),
                ServiceEndpoint(name="quant_factor_lab", base_url="http://lab"),
            ],
            health_client=FakeHealthClient(
                health_by_name={
                    "quant_data_hub": _make_health(name="quant_data_hub", status="ok"),
                    "quant_factor_lab": _make_health(name="quant_factor_lab", status="down"),
                }
            ),
        )

        response = await service.get_overview()

        self.assertEqual(response.status, "degraded")
        self.assertEqual(response.down_count, 1)

    def test_should_return_down_when_no_service_is_configured(self) -> None:
        response = build_overview_response(services=[])

        self.assertEqual(response.status, "down")
        self.assertEqual(response.service_count, 0)


def _make_health(*, name: str, status: str) -> ServiceHealth:
    return ServiceHealth(
        name=name,
        base_url=f"http://{name}",
        status=status,
        checked_at=datetime.now(timezone.utc),
    )


if __name__ == "__main__":
    unittest.main()
