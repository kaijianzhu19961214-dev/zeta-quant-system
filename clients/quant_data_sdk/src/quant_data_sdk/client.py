from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from datetime import date, datetime
from typing import Any

import httpx
from quant_contracts import MarketBarsQuery, MarketBarsResponse, PriceMode, Timeframe

from quant_data_sdk.schemas import HealthResponse, QfqBatchListResponse

DEFAULT_BASE_URL = "http://127.0.0.1:18000"


class QuantDataApiError(RuntimeError):
    def __init__(self, *, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class QuantDataClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_token: str | None = None,
        timeout: float = 10.0,
        transport: httpx.BaseTransport | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        normalized_base_url = _normalize_base_url(base_url)
        headers = _build_headers(api_token=api_token)

        self._is_owner = http_client is None
        self._client = http_client or httpx.Client(
            base_url=normalized_base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.market = MarketClient(http_client=self)
        self.adjustments = AdjustmentsClient(http_client=self)

    @classmethod
    def from_env(cls, *, timeout: float = 10.0) -> "QuantDataClient":
        return cls(
            base_url=os.getenv("QUANT_DATA_HUB_BASE_URL", DEFAULT_BASE_URL),
            api_token=os.getenv("QUANT_DATA_API_TOKEN") or None,
            timeout=timeout,
        )

    def close(self) -> None:
        if not self._is_owner:
            return
        self._client.close()

    def __enter__(self) -> "QuantDataClient":
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self.close()

    def health(self) -> HealthResponse:
        payload = self._request(method="GET", path="/health")
        return HealthResponse.model_validate(payload)

    def _request(
        self,
        *,
        method: str,
        path: str,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = self._client.request(method=method, url=path, json=json, params=params)
        except httpx.RequestError as error:
            raise QuantDataApiError(message=f"quant_data_hub request failed: {error.__class__.__name__}") from error

        return _parse_response(response=response)


class AsyncQuantDataClient:
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_token: str | None = None,
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        normalized_base_url = _normalize_base_url(base_url)
        headers = _build_headers(api_token=api_token)

        self._is_owner = http_client is None
        self._client = http_client or httpx.AsyncClient(
            base_url=normalized_base_url,
            headers=headers,
            timeout=timeout,
            transport=transport,
        )
        self.market = AsyncMarketClient(http_client=self)
        self.adjustments = AsyncAdjustmentsClient(http_client=self)

    @classmethod
    def from_env(cls, *, timeout: float = 10.0) -> "AsyncQuantDataClient":
        return cls(
            base_url=os.getenv("QUANT_DATA_HUB_BASE_URL", DEFAULT_BASE_URL),
            api_token=os.getenv("QUANT_DATA_API_TOKEN") or None,
            timeout=timeout,
        )

    async def close(self) -> None:
        if not self._is_owner:
            return
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncQuantDataClient":
        return self

    async def __aexit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        await self.close()

    async def health(self) -> HealthResponse:
        payload = await self._request(method="GET", path="/health")
        return HealthResponse.model_validate(payload)

    async def _request(
        self,
        *,
        method: str,
        path: str,
        json: Mapping[str, Any] | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        try:
            response = await self._client.request(method=method, url=path, json=json, params=params)
        except httpx.RequestError as error:
            raise QuantDataApiError(message=f"quant_data_hub request failed: {error.__class__.__name__}") from error

        return _parse_response(response=response)


class MarketClient:
    def __init__(self, *, http_client: QuantDataClient) -> None:
        self._http_client = http_client

    def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        payload = self._http_client._request(
            method="POST",
            path="/api/v1/market-bars/query",
            json=query.model_dump(mode="json"),
        )
        return MarketBarsResponse.model_validate(payload)

    def get_bars(
        self,
        *,
        symbols: Sequence[str],
        timeframe: Timeframe | str,
        start: date | datetime | str,
        end: date | datetime | str,
        price_mode: PriceMode | str = PriceMode.RAW,
        dataset_code: str | None = None,
        batch_id: str | None = None,
        fields: Sequence[str] | None = None,
        limit: int = 10000,
    ) -> MarketBarsResponse:
        query = MarketBarsQuery(
            timeframe=timeframe,
            symbols=_normalize_sequence(value=symbols, name="symbols"),
            start=start,
            end=end,
            price_mode=price_mode,
            dataset_code=dataset_code,
            batch_id=batch_id,
            fields=_normalize_optional_sequence(value=fields, name="fields"),
            limit=limit,
        )
        return self.query_bars(query=query)


class AdjustmentsClient:
    def __init__(self, *, http_client: QuantDataClient) -> None:
        self._http_client = http_client

    def list_qfq_batches(self, *, limit: int = 100) -> QfqBatchListResponse:
        payload = self._http_client._request(
            method="GET",
            path="/api/v1/adjustments/qfq-batches",
            params={"limit": limit},
        )
        return QfqBatchListResponse.model_validate(payload)


class AsyncMarketClient:
    def __init__(self, *, http_client: AsyncQuantDataClient) -> None:
        self._http_client = http_client

    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        payload = await self._http_client._request(
            method="POST",
            path="/api/v1/market-bars/query",
            json=query.model_dump(mode="json"),
        )
        return MarketBarsResponse.model_validate(payload)

    async def get_bars(
        self,
        *,
        symbols: Sequence[str],
        timeframe: Timeframe | str,
        start: date | datetime | str,
        end: date | datetime | str,
        price_mode: PriceMode | str = PriceMode.RAW,
        dataset_code: str | None = None,
        batch_id: str | None = None,
        fields: Sequence[str] | None = None,
        limit: int = 10000,
    ) -> MarketBarsResponse:
        query = MarketBarsQuery(
            timeframe=timeframe,
            symbols=_normalize_sequence(value=symbols, name="symbols"),
            start=start,
            end=end,
            price_mode=price_mode,
            dataset_code=dataset_code,
            batch_id=batch_id,
            fields=_normalize_optional_sequence(value=fields, name="fields"),
            limit=limit,
        )
        return await self.query_bars(query=query)


class AsyncAdjustmentsClient:
    def __init__(self, *, http_client: AsyncQuantDataClient) -> None:
        self._http_client = http_client

    async def list_qfq_batches(self, *, limit: int = 100) -> QfqBatchListResponse:
        payload = await self._http_client._request(
            method="GET",
            path="/api/v1/adjustments/qfq-batches",
            params={"limit": limit},
        )
        return QfqBatchListResponse.model_validate(payload)


def _normalize_base_url(base_url: str) -> str:
    normalized_base_url = base_url.strip().rstrip("/")
    if normalized_base_url:
        return normalized_base_url
    raise ValueError("base_url must not be empty")


def _build_headers(*, api_token: str | None) -> dict[str, str]:
    normalized_api_token = api_token.strip() if api_token else None
    if not normalized_api_token:
        return {}
    return {"Authorization": f"Bearer {normalized_api_token}"}


def _normalize_sequence(*, value: Sequence[str], name: str) -> list[str]:
    if isinstance(value, str):
        raise ValueError(f"{name} must be a sequence of strings, not a string")
    return list(value)


def _normalize_optional_sequence(*, value: Sequence[str] | None, name: str) -> list[str] | None:
    if value is None:
        return None
    return _normalize_sequence(value=value, name=name)


def _build_api_error(*, response: httpx.Response) -> QuantDataApiError:
    message = f"quant_data_hub returned HTTP {response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return QuantDataApiError(message=message, status_code=response.status_code)

    if not isinstance(payload, dict):
        return QuantDataApiError(message=message, status_code=response.status_code)

    detail = payload.get("detail")
    if isinstance(detail, str) and detail.strip():
        message = detail.strip()
    elif isinstance(detail, list):
        message = "quant_data_hub request validation failed"

    return QuantDataApiError(message=message, status_code=response.status_code)


def _parse_response(*, response: httpx.Response) -> dict[str, Any]:
    if response.status_code >= 400:
        raise _build_api_error(response=response)

    try:
        payload = response.json()
    except ValueError as error:
        raise QuantDataApiError(
            message="quant_data_hub returned an invalid JSON response",
            status_code=response.status_code,
        ) from error

    if not isinstance(payload, dict):
        raise QuantDataApiError(
            message="quant_data_hub returned a non-object response",
            status_code=response.status_code,
        )

    return payload
