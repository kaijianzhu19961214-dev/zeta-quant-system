from fastapi import APIRouter, Depends, HTTPException, status
from quant_contracts import FactorComparisonReport, FactorValidationRequest, FactorValidationResponse
from quant_data_sdk import QuantDataApiError

from quant_factor_validation.api.v1.dependencies import get_factor_validation_service
from quant_factor_validation.services.external_payload_comparison import (
    ExternalPayloadEvaluationSet,
    build_external_payload_comparison_report,
)
from quant_factor_validation.services.factor_validation_service import FactorValidationService

router = APIRouter(prefix="/api/v1", tags=["factor-validation"])


@router.post(
    "/factors/validate",
    response_model=FactorValidationResponse,
    summary="验证日频因子",
    description="读取标准行情计算 forward return，并返回 IC / Rank IC 摘要。",
)
async def post_factor_validation(
    request: FactorValidationRequest,
    service: FactorValidationService = Depends(get_factor_validation_service),
) -> FactorValidationResponse:
    try:
        return await service.validate(request=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except QuantDataApiError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post(
    "/factors/external-payloads/compare",
    response_model=FactorComparisonReport,
    summary="对比外部因子验证 payload",
    description="汇总 Alphalens / Qlib / vectorbt 标准化 payload，并返回统一因子对比报告。",
)
def post_external_payload_comparison(
    request: ExternalPayloadEvaluationSet,
) -> FactorComparisonReport:
    try:
        return build_external_payload_comparison_report(payload_set=request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
