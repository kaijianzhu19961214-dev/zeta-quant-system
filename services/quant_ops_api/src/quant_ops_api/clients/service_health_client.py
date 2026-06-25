from datetime import datetime, timezone
from time import perf_counter
from typing import Any

import httpx

from quant_ops_api.schemas import ServiceEndpoint, ServiceHealth


class ServiceHealthClient:
    def __init__(self, *, timeout_seconds: float) -> None:
        self.timeout_seconds = timeout_seconds

    async def fetch_health(self, *, endpoint: ServiceEndpoint) -> ServiceHealth:
        checked_at = datetime.now(timezone.utc)
        started_at = perf_counter()
        health_url = _build_health_url(endpoint=endpoint)

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(health_url)
        except httpx.TimeoutException:
            return _build_down_health(
                endpoint=endpoint,
                checked_at=checked_at,
                latency_ms=_calculate_latency_ms(started_at=started_at),
                error_message="health check timed out",
            )
        except httpx.HTTPError as error:
            return _build_down_health(
                endpoint=endpoint,
                checked_at=checked_at,
                latency_ms=_calculate_latency_ms(started_at=started_at),
                error_message=str(error),
            )

        latency_ms = _calculate_latency_ms(started_at=started_at)
        if response.status_code < 200 or response.status_code >= 300:
            return ServiceHealth(
                name=endpoint.name,
                base_url=endpoint.base_url,
                status="down",
                checked_at=checked_at,
                latency_ms=latency_ms,
                http_status_code=response.status_code,
                error_message=f"unexpected http status {response.status_code}",
            )

        return _parse_health_response(
            endpoint=endpoint,
            checked_at=checked_at,
            latency_ms=latency_ms,
            status_code=response.status_code,
            payload=_safe_json(response=response),
        )


def _build_health_url(*, endpoint: ServiceEndpoint) -> str:
    return f"{endpoint.base_url.rstrip('/')}/{endpoint.health_path.lstrip('/')}"


def _calculate_latency_ms(*, started_at: float) -> float:
    return round((perf_counter() - started_at) * 1000, 2)


def _safe_json(*, response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _parse_health_response(
    *,
    endpoint: ServiceEndpoint,
    checked_at: datetime,
    latency_ms: float,
    status_code: int,
    payload: dict[str, Any] | None,
) -> ServiceHealth:
    if payload is None:
        return ServiceHealth(
            name=endpoint.name,
            base_url=endpoint.base_url,
            status="degraded",
            checked_at=checked_at,
            latency_ms=latency_ms,
            http_status_code=status_code,
            error_message="health response is not a JSON object",
        )

    service_status = str(payload.get("status", "")).lower()
    if service_status != "ok":
        return ServiceHealth(
            name=endpoint.name,
            base_url=endpoint.base_url,
            status="degraded",
            checked_at=checked_at,
            latency_ms=latency_ms,
            http_status_code=status_code,
            error_message="health response status is not ok",
        )

    return ServiceHealth(
        name=endpoint.name,
        base_url=endpoint.base_url,
        status="ok",
        checked_at=checked_at,
        latency_ms=latency_ms,
        http_status_code=status_code,
    )


def _build_down_health(
    *,
    endpoint: ServiceEndpoint,
    checked_at: datetime,
    latency_ms: float,
    error_message: str,
) -> ServiceHealth:
    return ServiceHealth(
        name=endpoint.name,
        base_url=endpoint.base_url,
        status="down",
        checked_at=checked_at,
        latency_ms=latency_ms,
        error_message=error_message,
    )
