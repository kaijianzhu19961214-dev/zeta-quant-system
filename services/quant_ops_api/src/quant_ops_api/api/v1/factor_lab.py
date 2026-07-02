from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from quant_contracts import (
    AlgorithmPromotionReadinessResponse,
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceResponse,
    AlgorithmSpec,
    FactorCalculationRequest,
    FactorCalculationResponse,
)

from quant_ops_api.api.v1.dependencies import get_factor_lab_client
from quant_ops_api.clients import FactorLabClient, FactorLabClientError

router = APIRouter(prefix="/api/v1/factor-lab", tags=["factor-lab"])


def build_momentum_1d_sample_request() -> FactorCalculationRequest:
    return FactorCalculationRequest(
        factor_name="momentum_1d",
        algorithm_id="technical.momentum",
        symbols=["000001.SZ"],
        start="2026-06-09",
        end="2026-06-10",
        price_mode="raw",
        lookback_window=1,
        run_id="ops_real_sample_momentum_1d",
        limit=10,
    )


@router.get("/algorithms", response_model=list[AlgorithmSpec])
async def read_factor_lab_algorithms(
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
) -> list[AlgorithmSpec]:
    try:
        return await factor_lab_client.list_algorithms()
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error


@router.get(
    "/factors/samples/momentum-1d",
    response_model=FactorCalculationResponse,
)
async def read_factor_lab_momentum_1d_sample(
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
) -> FactorCalculationResponse:
    try:
        return await factor_lab_client.calculate_factor(request=build_momentum_1d_sample_request())
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error


@router.get(
    "/algorithms/{algorithm_id}/review-gates/evidence",
    response_model=AlgorithmReviewGateEvidenceListResponse,
)
async def read_factor_lab_algorithm_review_gate_evidence(
    algorithm_id: str,
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
    gate_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
) -> AlgorithmReviewGateEvidenceListResponse:
    try:
        return await factor_lab_client.list_algorithm_review_gate_evidence(
            algorithm_id=algorithm_id,
            gate_id=gate_id,
            limit=limit,
        )
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error


@router.post(
    "/algorithms/review-gates/evidence/{evidence_id}/review",
    response_model=AlgorithmReviewGateEvidenceResponse,
)
async def review_factor_lab_algorithm_review_gate_evidence(
    evidence_id: str,
    request: AlgorithmReviewGateEvidenceReviewRequest,
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
) -> AlgorithmReviewGateEvidenceResponse:
    try:
        return await factor_lab_client.review_algorithm_review_gate_evidence(
            evidence_id=evidence_id,
            request=request,
        )
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error


@router.get(
    "/algorithms/{algorithm_id}/promotion/readiness",
    response_model=AlgorithmPromotionReadinessResponse,
)
async def read_factor_lab_algorithm_promotion_readiness(
    algorithm_id: str,
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
    limit: int = Query(default=200, ge=1, le=500),
) -> AlgorithmPromotionReadinessResponse:
    try:
        return await factor_lab_client.get_algorithm_promotion_readiness(
            algorithm_id=algorithm_id,
            limit=limit,
        )
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error
