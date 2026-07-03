from fastapi import APIRouter, Depends, HTTPException, Query, status

from quant_data_hub.api.v1.dependencies import get_market_query_service
from quant_data_hub.schemas.ingestion_ledger import IngestionLedgerPreviewResponse
from quant_data_hub.services.ingestion_ledger_service import IngestionLedgerService
from quant_data_hub.services.market_query_service import MarketQueryService

router = APIRouter(prefix="/api/v1/ingestion", tags=["ingestion-ledger"])


@router.get(
    "/ledger/preview",
    response_model=IngestionLedgerPreviewResponse,
    summary="预览数据导入账本",
    description="从 ClickHouse 覆盖率派生导入批次和质量检查记录，当前不写 PostgreSQL。",
)
async def preview_ingestion_ledger(
    limit: int = Query(default=100, ge=1, le=1000, description="最大读取覆盖率行数"),
    market_query_service: MarketQueryService = Depends(get_market_query_service),
) -> IngestionLedgerPreviewResponse:
    service = IngestionLedgerService(market_query_service=market_query_service)
    try:
        return await service.preview_ledger(limit=limit)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error
