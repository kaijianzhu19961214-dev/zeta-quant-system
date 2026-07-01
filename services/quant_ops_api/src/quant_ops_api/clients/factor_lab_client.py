from typing import Any

import httpx
from quant_contracts import AlgorithmSpec


class FactorLabClientError(Exception):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class FactorLabClient:
    def __init__(
        self,
        *,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.transport = transport

    async def list_algorithms(self) -> list[AlgorithmSpec]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(f"{self.base_url}/api/v1/algorithms")
        except httpx.TimeoutException as error:
            raise FactorLabClientError(
                status_code=504,
                message="factor lab algorithm registry request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab algorithm registry request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab algorithm registry returned status {response.status_code}",
            )

        return _parse_algorithm_specs(response=response)


def _parse_algorithm_specs(*, response: httpx.Response) -> list[AlgorithmSpec]:
    payload = _safe_json(response=response)
    if payload is None:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab algorithm registry response is not valid JSON",
        )

    try:
        return [AlgorithmSpec.model_validate(item) for item in payload]
    except ValueError as error:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab algorithm registry response does not match the contract",
        ) from error


def _safe_json(*, response: httpx.Response) -> list[dict[str, Any]] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if not isinstance(payload, list):
        return None
    if all(isinstance(item, dict) for item in payload):
        return payload
    return None
