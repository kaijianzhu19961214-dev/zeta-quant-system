from typing import Any

import httpx
from quant_contracts import FactorComparisonReport

from quant_ops_api.schemas import ExternalPayloadComparisonRequest


class FactorValidationClientError(Exception):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class FactorValidationClient:
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

    async def compare_external_payloads(
        self,
        *,
        request: ExternalPayloadComparisonRequest,
    ) -> FactorComparisonReport:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/factors/external-payloads/compare",
                    json=request.model_dump(mode="json"),
                )
        except httpx.TimeoutException as error:
            raise FactorValidationClientError(
                status_code=504,
                message="factor validation comparison request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise FactorValidationClientError(
                status_code=502,
                message=f"factor validation comparison request failed: {error}",
            ) from error

        if response.status_code == 422:
            raise FactorValidationClientError(
                status_code=422,
                message=_extract_error_message(payload=_safe_json(response=response)),
            )
        if response.status_code < 200 or response.status_code >= 300:
            raise FactorValidationClientError(
                status_code=502,
                message=f"factor validation comparison returned status {response.status_code}",
            )

        return _parse_comparison_report(response=response)


def _parse_comparison_report(*, response: httpx.Response) -> FactorComparisonReport:
    payload = _safe_json(response=response)
    if payload is None:
        raise FactorValidationClientError(
            status_code=502,
            message="factor validation comparison response is not valid JSON",
        )

    try:
        return FactorComparisonReport.model_validate(payload)
    except ValueError as error:
        raise FactorValidationClientError(
            status_code=502,
            message="factor validation comparison response does not match the contract",
        ) from error


def _safe_json(*, response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _extract_error_message(*, payload: dict[str, Any] | None) -> str:
    if payload is None:
        return "factor validation comparison request was rejected"

    detail = payload.get("detail")
    if isinstance(detail, str) and detail:
        return detail
    return "factor validation comparison request was rejected"
