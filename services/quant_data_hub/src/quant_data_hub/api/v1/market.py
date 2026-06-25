from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import ValidationError
from quant_contracts import MarketBarsQuery, MarketBarsResponse, PriceMode, Timeframe

from quant_data_hub.api.v1.dependencies import get_market_query_service
from quant_data_hub.schemas.adjustment import QfqBatchListResponse
from quant_data_hub.schemas.legacy_market import LegacyMarketBarsQueryRequest
from quant_data_hub.services.market_query_service import MarketQueryService

router = APIRouter(prefix="/api/v1", tags=["market-query"])


@router.post(
    "/market-bars/query",
    response_model=MarketBarsResponse,
    summary="查询标准行情 K 线数据",
    description="使用 quant_contracts 标准字段查询 ClickHouse 行情数据。",
)
async def post_market_bars_query(
    request: MarketBarsQuery,
    service: MarketQueryService = Depends(get_market_query_service),
) -> MarketBarsResponse:
    return await query_market_bars(request=request, service=service)


@router.post(
    "/market/bars/query",
    response_model=MarketBarsResponse,
    summary="兼容旧项目行情 K 线查询",
    description="兼容旧项目 codes/date/vol/amount 字段，请求进入服务后转换为 quant_contracts 标准协议。",
)
async def post_legacy_market_bars_query(
    request: LegacyMarketBarsQueryRequest,
    service: MarketQueryService = Depends(get_market_query_service),
) -> MarketBarsResponse:
    return await query_market_bars(request=request.to_contract_query(), service=service)


@router.get(
    "/market/bars",
    response_model=MarketBarsResponse,
    summary="兼容旧项目 GET 行情查询",
    description="短股票列表可用 GET；长股票池建议使用 POST /api/v1/market-bars/query。",
)
async def get_legacy_market_bars(
    timeframe: Timeframe = Query(description="行情频率：1m、5m、1d"),
    codes: str = Query(description="逗号分隔证券代码，例如 000001.SZ,000651.SZ"),
    start: str = Query(description="开始日期或时间"),
    end: str = Query(description="结束日期或时间"),
    price_mode: PriceMode = Query(default=PriceMode.RAW, description="价格口径：raw、qfq、hfq"),
    dataset_code: str | None = Query(default=None, description="数据集编码"),
    batch_id: str | None = Query(default=None, description="前复权批次"),
    fields: str | None = Query(default=None, description="逗号分隔返回字段"),
    limit: int = Query(default=10000, ge=1, le=100000, description="最大返回行数"),
    service: MarketQueryService = Depends(get_market_query_service),
) -> MarketBarsResponse:
    try:
        request = LegacyMarketBarsQueryRequest(
            timeframe=timeframe,
            codes=[code.strip() for code in codes.split(",")],
            start=start,
            end=end,
            price_mode=price_mode,
            dataset_code=dataset_code,
            batch_id=batch_id,
            fields=[field.strip() for field in fields.split(",")] if fields else None,
            limit=limit,
        )
    except ValidationError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=error.errors()) from error

    return await query_market_bars(request=request.to_contract_query(), service=service)


@router.get(
    "/adjustments/qfq-batches",
    response_model=QfqBatchListResponse,
    summary="查询前复权批次",
    description="查询 ClickHouse 中已经生成的 qfq 批次，用于 price_mode=qfq 的 batch_id 参数。",
)
async def list_qfq_batches(
    limit: int = Query(default=100, ge=1, le=1000, description="最大返回批次数"),
    service: MarketQueryService = Depends(get_market_query_service),
) -> QfqBatchListResponse:
    try:
        return await service.list_qfq_batches(limit=limit)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


async def query_market_bars(
    *,
    request: MarketBarsQuery,
    service: MarketQueryService,
) -> MarketBarsResponse:
    try:
        return await service.query_bars(request)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error

