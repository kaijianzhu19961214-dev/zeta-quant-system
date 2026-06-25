from typing import Annotated

from fastapi import APIRouter, Depends

from quant_ops_api.api.v1.dependencies import get_factor_validation_review_service
from quant_ops_api.schemas import FactorValidationReviewResponse
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
