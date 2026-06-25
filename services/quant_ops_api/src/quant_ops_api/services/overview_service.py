import asyncio
from datetime import datetime, timezone

from quant_ops_api.clients import ServiceHealthClient
from quant_ops_api.schemas import OpsOverviewResponse, ServiceEndpoint, ServiceHealth


class OverviewService:
    def __init__(
        self,
        *,
        endpoints: list[ServiceEndpoint],
        health_client: ServiceHealthClient,
    ) -> None:
        self.endpoints = endpoints
        self.health_client = health_client

    async def get_overview(self) -> OpsOverviewResponse:
        service_health = await asyncio.gather(
            *[self.health_client.fetch_health(endpoint=endpoint) for endpoint in self.endpoints]
        )
        return build_overview_response(services=list(service_health))


def build_overview_response(*, services: list[ServiceHealth]) -> OpsOverviewResponse:
    healthy_count = sum(1 for service in services if service.status == "ok")
    degraded_count = sum(1 for service in services if service.status == "degraded")
    down_count = sum(1 for service in services if service.status == "down")

    return OpsOverviewResponse(
        status=_resolve_overview_status(
            service_count=len(services),
            healthy_count=healthy_count,
            degraded_count=degraded_count,
            down_count=down_count,
        ),
        generated_at=datetime.now(timezone.utc),
        services=services,
        service_count=len(services),
        healthy_count=healthy_count,
        degraded_count=degraded_count,
        down_count=down_count,
    )


def _resolve_overview_status(
    *,
    service_count: int,
    healthy_count: int,
    degraded_count: int,
    down_count: int,
) -> str:
    if service_count == 0:
        return "down"
    if healthy_count == service_count:
        return "ok"
    if down_count == service_count:
        return "down"
    if degraded_count > 0 or down_count > 0:
        return "degraded"
    return "down"
