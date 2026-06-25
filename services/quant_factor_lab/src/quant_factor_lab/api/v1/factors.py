from fastapi import APIRouter, Depends, HTTPException, status
from quant_contracts import FactorCalculationRequest, FactorCalculationResponse
from quant_data_sdk import QuantDataApiError

from quant_factor_lab.api.v1.dependencies import get_factor_calculation_service
from quant_factor_lab.services.factor_calculation_service import FactorCalculationService

router = APIRouter(prefix="/api/v1", tags=["factor-calculation"])


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
