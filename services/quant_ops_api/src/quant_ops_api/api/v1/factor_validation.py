from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from quant_contracts import FactorComparisonReport

from quant_ops_api.api.v1.dependencies import (
    get_factor_validation_client,
    get_factor_validation_review_service,
)
from quant_ops_api.clients import FactorValidationClient, FactorValidationClientError
from quant_ops_api.schemas import ExternalPayloadComparisonRequest, FactorValidationReviewResponse
from quant_ops_api.services import FactorValidationReviewService

router = APIRouter(prefix="/api/v1/factor-validation", tags=["factor-validation"])


@router.get("/review", response_model=FactorValidationReviewResponse)
def read_factor_validation_review(
    review_service: Annotated[
        FactorValidationReviewService,
        Depends(get_factor_validation_review_service),
    ],
) -> FactorValidationReviewResponse:
    return review_service.get_review()


@router.post("/external-payloads/compare", response_model=FactorComparisonReport)
async def compare_external_payloads(
    request: ExternalPayloadComparisonRequest,
    validation_client: Annotated[
        FactorValidationClient,
        Depends(get_factor_validation_client),
    ],
) -> FactorComparisonReport:
    try:
        return await validation_client.compare_external_payloads(request=request)
    except FactorValidationClientError as error:
        if error.status_code in {
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_504_GATEWAY_TIMEOUT,
        }:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error
