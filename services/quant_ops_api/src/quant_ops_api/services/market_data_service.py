from datetime import datetime, timezone

from quant_contracts import MarketBarsQuery, PriceMode, Timeframe

from quant_ops_api.clients import QuantDataHubClient
from quant_ops_api.schemas import (
    MarketDataBarsSampleRequest,
    MarketDataBarsSampleResponse,
    MarketDataPriceModeOverview,
    MarketPriceModeStatus,
    QfqBatchSummary,
)


class MarketDataService:
    def __init__(self, *, quant_data_hub_client: QuantDataHubClient, qfq_batch_limit: int = 20) -> None:
        self.quant_data_hub_client = quant_data_hub_client
        self.qfq_batch_limit = qfq_batch_limit

    async def get_price_mode_overview(self) -> MarketDataPriceModeOverview:
        qfq_batches = await self.quant_data_hub_client.list_qfq_batches(limit=self.qfq_batch_limit)
        return build_price_mode_overview(qfq_batches=qfq_batches)

    async def query_sample_bars(self, *, request: MarketDataBarsSampleRequest) -> MarketDataBarsSampleResponse:
        qfq_batch = await self.find_sample_qfq_batch(request=request)
        if request.price_mode == "qfq" and qfq_batch is not None:
            resolved_request = request.model_copy(update={"batch_id": qfq_batch.batch_id})
        elif request.price_mode == "qfq":
            resolved_request = request
        else:
            resolved_request = request.model_copy(update={"batch_id": None})

        market_query = MarketBarsQuery(
            timeframe=Timeframe(resolved_request.timeframe),
            symbols=[resolved_request.symbol],
            start=resolved_request.start,
            end=resolved_request.end,
            price_mode=PriceMode(resolved_request.price_mode),
            batch_id=resolved_request.batch_id,
            fields=resolved_request.fields,
            limit=resolved_request.limit,
        )
        market_response = await self.quant_data_hub_client.query_market_bars(request=market_query)
        meta = market_response.meta
        if qfq_batch is not None and meta.qfq_base_date is None:
            meta = meta.model_copy(update={"qfq_base_date": qfq_batch.qfq_base_date})

        return MarketDataBarsSampleResponse(
            generated_at=datetime.now(timezone.utc),
            request=resolved_request,
            meta=meta,
            rows=market_response.rows,
            limitations=[
                "This endpoint is for read-only smoke preview only; limit is capped at 20 rows.",
                "Use quant_data_hub market-bars API for controlled service-to-service factor pipelines.",
            ],
        )

    async def find_sample_qfq_batch(
        self,
        *,
        request: MarketDataBarsSampleRequest,
    ) -> QfqBatchSummary | None:
        if request.price_mode != "qfq":
            return None

        if request.batch_id:
            qfq_batches = await self.quant_data_hub_client.list_qfq_batches(limit=self.qfq_batch_limit)
            return next((qfq_batch for qfq_batch in qfq_batches if qfq_batch.batch_id == request.batch_id), None)

        qfq_batches = await self.quant_data_hub_client.list_qfq_batches(limit=1)
        if not qfq_batches:
            raise ValueError("qfq batch_id is required but no qfq batch is available")

        return qfq_batches[0]


def build_price_mode_overview(*, qfq_batches: list[QfqBatchSummary]) -> MarketDataPriceModeOverview:
    latest_qfq_batch = qfq_batches[0] if qfq_batches else None
    return MarketDataPriceModeOverview(
        status="ok" if latest_qfq_batch is not None else "degraded",
        generated_at=datetime.now(timezone.utc),
        qfq_batch_count=len(qfq_batches),
        latest_qfq_batch=latest_qfq_batch,
        price_modes=[
            MarketPriceModeStatus(
                price_mode="raw",
                display_name="原始价格 / Raw",
                storage_object="market_data_*_raw",
                source_relation="Direct ClickHouse raw table query.",
                requires_batch_id=False,
                available=True,
            ),
            MarketPriceModeStatus(
                price_mode="qfq",
                display_name="前复权 / QFQ",
                storage_object="market_data_*_qfq_cache",
                source_relation="QFQ cache joined with raw table for non-price fields.",
                requires_batch_id=True,
                available=latest_qfq_batch is not None,
                latest_batch_id=latest_qfq_batch.batch_id if latest_qfq_batch is not None else None,
                latest_qfq_base_date=latest_qfq_batch.qfq_base_date if latest_qfq_batch is not None else None,
            ),
            MarketPriceModeStatus(
                price_mode="hfq",
                display_name="后复权 / HFQ",
                storage_object="v_market_data_*_hfq",
                source_relation="ClickHouse view calculates raw price multiplied by hfq_factor.",
                requires_batch_id=False,
                available=True,
            ),
        ],
        limitations=[
            "price_mode=qfq requires an explicit batch_id when querying market bars.",
            "MarketBar.adjustment_factor is the effective factor for the selected price_mode.",
        ],
    )
