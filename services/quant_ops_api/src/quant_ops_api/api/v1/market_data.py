from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from quant_ops_api.api.v1.dependencies import get_market_data_service
from quant_ops_api.clients import QuantDataHubClientError
from quant_ops_api.schemas import (
    MarketDataBarsSampleRequest,
    MarketDataBarsSampleResponse,
    MarketDataPriceModeOverview,
)
from quant_ops_api.services import MarketDataService

router = APIRouter(prefix="/api/v1/market-data", tags=["market-data"])


@router.get("/price-modes", response_model=MarketDataPriceModeOverview)
async def read_market_data_price_modes(
    market_data_service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> MarketDataPriceModeOverview:
    try:
        return await market_data_service.get_price_mode_overview()
    except QuantDataHubClientError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error


@router.post("/bars/sample", response_model=MarketDataBarsSampleResponse)
async def read_market_data_bars_sample(
    request: MarketDataBarsSampleRequest,
    market_data_service: Annotated[MarketDataService, Depends(get_market_data_service)],
) -> MarketDataBarsSampleResponse:
    try:
        return await market_data_service.query_sample_bars(request=request)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except QuantDataHubClientError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from error
