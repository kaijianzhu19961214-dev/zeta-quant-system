from typing import Any

import httpx
from quant_contracts import (
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceResponse,
    AlgorithmSpec,
)


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

    async def list_algorithm_review_gate_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> AlgorithmReviewGateEvidenceListResponse:
        params: dict[str, str | int] = {"limit": limit}
        if gate_id is not None:
            params["gate_id"] = gate_id

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.get(
                    f"{self.base_url}/api/v1/algorithms/{algorithm_id}/review-gates/evidence",
                    params=params,
                )
        except httpx.TimeoutException as error:
            raise FactorLabClientError(
                status_code=504,
                message="factor lab review evidence request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab review evidence request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab review evidence returned status {response.status_code}",
            )

        return _parse_algorithm_review_gate_evidence(response=response)

    async def review_algorithm_review_gate_evidence(
        self,
        *,
        evidence_id: str,
        request: AlgorithmReviewGateEvidenceReviewRequest,
    ) -> AlgorithmReviewGateEvidenceResponse:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self.transport,
            ) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/algorithms/review-gates/evidence/{evidence_id}/review",
                    json=request.model_dump(mode="json"),
                )
        except httpx.TimeoutException as error:
            raise FactorLabClientError(
                status_code=504,
                message="factor lab review decision request timed out",
            ) from error
        except httpx.HTTPError as error:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab review decision request failed: {error}",
            ) from error

        if response.status_code < 200 or response.status_code >= 300:
            raise FactorLabClientError(
                status_code=502,
                message=f"factor lab review decision returned status {response.status_code}",
            )

        return _parse_algorithm_review_gate_evidence_response(response=response)


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


def _parse_algorithm_review_gate_evidence(
    *,
    response: httpx.Response,
) -> AlgorithmReviewGateEvidenceListResponse:
    payload = _safe_dict_json(response=response)
    if payload is None:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab review evidence response is not valid JSON",
        )

    try:
        return AlgorithmReviewGateEvidenceListResponse.model_validate(payload)
    except ValueError as error:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab review evidence response does not match the contract",
        ) from error


def _parse_algorithm_review_gate_evidence_response(
    *,
    response: httpx.Response,
) -> AlgorithmReviewGateEvidenceResponse:
    payload = _safe_dict_json(response=response)
    if payload is None:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab review decision response is not valid JSON",
        )

    try:
        return AlgorithmReviewGateEvidenceResponse.model_validate(payload)
    except ValueError as error:
        raise FactorLabClientError(
            status_code=502,
            message="factor lab review decision response does not match the contract",
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


def _safe_dict_json(*, response: httpx.Response) -> dict[str, Any] | None:
    try:
        payload = response.json()
    except ValueError:
        return None

    if isinstance(payload, dict):
        return payload
    return None
