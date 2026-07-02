from typing import Any

import httpx
from quant_contracts import MarketBarsQuery, MarketBarsResponse

from quant_ops_api.schemas import MarketDataSourceCoverageItem, QfqBatchSummary


class QuantDataHubClientError(Exception):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class QuantDataHubClient:
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

    async def list_qfq_batches(self, *, limit: int = 20) -> list[QfqBatchSummary]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/adjustments/qfq-batches",
                    params={"limit": limit},
                )
        except httpx.TimeoutException as error:
            raise QuantDataHubClientError(
                status_code=504,
                message="quant data hub qfq batch request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub qfq batch request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub qfq batch request returned status {response.status_code}",
            )

        return _parse_qfq_batches(response=response)

    async def query_market_bars(self, *, request: MarketBarsQuery) -> MarketBarsResponse:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/market-bars/query",
                    json=request.model_dump(mode="json"),
                )
        except httpx.TimeoutException as error:
            raise QuantDataHubClientError(
                status_code=504,
                message="quant data hub market bars request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub market bars request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub market bars request returned status {response.status_code}",
            )

        return _parse_market_bars_response(response=response)

    async def get_source_coverage(self, *, limit: int = 100) -> list[MarketDataSourceCoverageItem]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/market-data/source-coverage",
                    params={"limit": limit},
                )
        except httpx.TimeoutException as error:
            raise QuantDataHubClientError(
                status_code=504,
                message="quant data hub source coverage request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub source coverage request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise QuantDataHubClientError(
                status_code=502,
                message=f"quant data hub source coverage request returned status {response.status_code}",
            )

        return _parse_source_coverage_response(response=response)


def _parse_qfq_batches(*, response: httpx.Response) -> list[QfqBatchSummary]:
    payload = _safe_json(response=response)
    if not isinstance(payload, dict):
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub qfq batch response is not a JSON object",
        )

    batches = payload.get("batches")
    if not isinstance(batches, list):
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub qfq batch response does not contain batches",
        )

    try:
        return [QfqBatchSummary.model_validate(item) for item in batches]
    except ValueError as error:
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub qfq batch response does not match the contract",
        ) from error


def _parse_market_bars_response(*, response: httpx.Response) -> MarketBarsResponse:
    payload = _safe_json(response=response)
    if not isinstance(payload, dict):
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub market bars response is not a JSON object",
        )

    try:
        return MarketBarsResponse.model_validate(payload)
    except ValueError as error:
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub market bars response does not match the contract",
        ) from error


def _parse_source_coverage_response(*, response: httpx.Response) -> list[MarketDataSourceCoverageItem]:
    payload = _safe_json(response=response)
    if not isinstance(payload, dict):
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub source coverage response is not a JSON object",
        )

    coverage = payload.get("coverage")
    if not isinstance(coverage, list):
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub source coverage response does not contain coverage",
        )

    try:
        return [MarketDataSourceCoverageItem.model_validate(item) for item in coverage]
    except ValueError as error:
        raise QuantDataHubClientError(
            status_code=502,
            message="quant data hub source coverage response does not match the contract",
        ) from error


def _safe_json(*, response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
