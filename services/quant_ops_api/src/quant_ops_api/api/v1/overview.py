from typing import Annotated

from fastapi import APIRouter, Depends

from quant_ops_api.api.v1.dependencies import get_overview_service
from quant_ops_api.schemas import OpsOverviewResponse
from quant_ops_api.services import OverviewService

router = APIRouter(prefix="/api/v1", tags=["overview"])


@router.get("/overview", response_model=OpsOverviewResponse)
async def read_overview(
    overview_service: Annotated[OverviewService, Depends(get_overview_service)],
) -> OpsOverviewResponse:
    return await overview_service.get_overview()
