from fastapi import APIRouter, Depends, HTTPException, Query, status
from quant_contracts import (
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceResponse,
    AlgorithmReviewGateEvidenceSubmission,
    AlgorithmSpec,
    FactorCalculationRequest,
    FactorCalculationResponse,
)
from quant_data_sdk import QuantDataApiError

from quant_factor_lab.api.v1.dependencies import get_algorithm_review_service, get_factor_calculation_service
from quant_factor_lab.services.algorithm_review_service import AlgorithmReviewService, AlgorithmReviewServiceError
from quant_factor_lab.services.factor_calculation_service import FactorCalculationService

router = APIRouter(prefix="/api/v1", tags=["factor-calculation"])


@router.get(
    "/algorithms",
    response_model=list[AlgorithmSpec],
    summary="列出算法适配器",
    description="返回 quant_factor_lab 当前可用和计划接入的因子算法规格。",
)
def get_algorithm_specs(
    service: FactorCalculationService = Depends(get_factor_calculation_service),
) -> list[AlgorithmSpec]:
    return service.list_algorithms()


@router.post(
    "/algorithms/review-gates/evidence/preview",
    response_model=AlgorithmReviewGateEvidenceResponse,
    summary="预览算法审核门槛证据记录",
    description="校验 algorithm_id 和 gate_id，并返回标准化 evidence record。MVP 不持久化记录。",
)
def post_algorithm_review_gate_evidence_preview(
    request: AlgorithmReviewGateEvidenceSubmission,
    service: AlgorithmReviewService = Depends(get_algorithm_review_service),
) -> AlgorithmReviewGateEvidenceResponse:
    try:
        return service.preview_evidence_record(submission=request)
    except AlgorithmReviewServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.post(
    "/algorithms/review-gates/evidence",
    response_model=AlgorithmReviewGateEvidenceResponse,
    summary="提交算法审核门槛证据记录",
    description="校验 algorithm_id 和 gate_id，将标准化 evidence record 写入审核证据库。",
)
async def post_algorithm_review_gate_evidence(
    request: AlgorithmReviewGateEvidenceSubmission,
    service: AlgorithmReviewService = Depends(get_algorithm_review_service),
) -> AlgorithmReviewGateEvidenceResponse:
    try:
        return await service.submit_evidence_record(submission=request)
    except AlgorithmReviewServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.post(
    "/algorithms/review-gates/evidence/{evidence_id}/review",
    response_model=AlgorithmReviewGateEvidenceResponse,
    summary="审核算法审核门槛证据记录",
    description="将已提交的 evidence record 标记为 accepted 或 rejected，并记录审核人和审核意见。",
)
async def post_algorithm_review_gate_evidence_review(
    evidence_id: str,
    request: AlgorithmReviewGateEvidenceReviewRequest,
    service: AlgorithmReviewService = Depends(get_algorithm_review_service),
) -> AlgorithmReviewGateEvidenceResponse:
    try:
        return await service.review_evidence_record(evidence_id=evidence_id, request=request)
    except AlgorithmReviewServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.get(
    "/algorithms/{algorithm_id}/review-gates/evidence",
    response_model=AlgorithmReviewGateEvidenceListResponse,
    summary="读取算法审核门槛证据记录",
    description="按 algorithm_id 和可选 gate_id 返回最近的审核证据记录。",
)
async def get_algorithm_review_gate_evidence(
    algorithm_id: str,
    gate_id: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    service: AlgorithmReviewService = Depends(get_algorithm_review_service),
) -> AlgorithmReviewGateEvidenceListResponse:
    try:
        return await service.list_evidence_records(
            algorithm_id=algorithm_id,
            gate_id=gate_id,
            limit=limit,
        )
    except AlgorithmReviewServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.post(
    "/factors/calculate",
    response_model=FactorCalculationResponse,
    summary="计算日频因子",
    description="从 quant_data_hub 标准行情接口读取数据，并返回标准因子值。",
)
async def post_factor_calculation(
    request: FactorCalculationRequest,
    service: FactorCalculationService = Depends(get_factor_calculation_service),
) -> FactorCalculationResponse:
    try:
        return await service.calculate(request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except QuantDataApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
