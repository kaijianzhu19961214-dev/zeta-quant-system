from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from quant_contracts import AlgorithmReviewGateEvidenceListResponse, AlgorithmSpec

from quant_ops_api.api.v1.dependencies import get_factor_lab_client
from quant_ops_api.clients import FactorLabClient, FactorLabClientError

router = APIRouter(prefix="/api/v1/factor-lab", tags=["factor-lab"])


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
