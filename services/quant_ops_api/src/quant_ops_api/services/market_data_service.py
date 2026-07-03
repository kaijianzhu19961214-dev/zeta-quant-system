from datetime import datetime, timezone

from quant_contracts import MarketBarsQuery, PriceMode, Timeframe

from quant_ops_api.clients import QuantDataHubClient
from quant_ops_api.schemas import (
    MarketDataBarsSampleRequest,
    MarketDataBarsSampleResponse,
    MarketDataIngestionLedgerPreview,
    MarketDataIngestionLedgerResponse,
    MarketDataPriceModeOverview,
    MarketPriceModeStatus,
    MarketDataSourceCoverageItem,
    MarketDataSourceCoverageResponse,
    MarketDataStorageRole,
    QfqBatchSummary,
)


class MarketDataService:
    def __init__(self, *, quant_data_hub_client: QuantDataHubClient, qfq_batch_limit: int = 20) -> None:
        self.quant_data_hub_client = quant_data_hub_client
        self.qfq_batch_limit = qfq_batch_limit

    async def get_price_mode_overview(self) -> MarketDataPriceModeOverview:
        qfq_batches = await self.quant_data_hub_client.list_qfq_batches(limit=self.qfq_batch_limit)
        return build_price_mode_overview(qfq_batches=qfq_batches)

    async def get_source_coverage(self, *, limit: int = 100) -> MarketDataSourceCoverageResponse:
        coverage: list[MarketDataSourceCoverageItem] = await self.quant_data_hub_client.get_source_coverage(limit=limit)
        duplicate_rows = sum(item.duplicate_key_rows for item in coverage)
        return MarketDataSourceCoverageResponse(
            status="ok" if coverage and duplicate_rows == 0 else "degraded",
            generated_at=datetime.now(timezone.utc),
            row_count=len(coverage),
            coverage=coverage,
            storage_roles=build_market_data_storage_roles(),
            limitations=[
                "ClickHouse is the source of truth for full market bar detail queries.",
                "PostgreSQL records ingestion/export tasks, metadata, lineage, and quality checks.",
                "MinIO stores raw responses, Parquet snapshots, and artifacts when archival is enabled.",
            ],
        )

    async def get_ingestion_ledger_preview(self, *, limit: int = 100) -> MarketDataIngestionLedgerResponse:
        preview = await self.quant_data_hub_client.get_ingestion_ledger_preview(limit=limit)
        return build_ingestion_ledger_response(preview=preview)

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


def build_market_data_storage_roles() -> list[MarketDataStorageRole]:
    return [
        MarketDataStorageRole(
            storage_name="postgresql",
            display_name="PostgreSQL",
            responsibility="控制面：导入导出任务、批次、元数据、血缘、质量检查和审核记录。",
            current_usage="当前不保存全量行情明细；下一步补导入批次和质量检查账本。",
            stores_market_bars=False,
        ),
        MarketDataStorageRole(
            storage_name="clickhouse",
            display_name="ClickHouse",
            responsibility="行情与因子分析主库：raw/qfq/hfq 明细查询、因子明细和聚合分析。",
            current_usage="当前 Tushare A 股日线明细已写入 quant_market.market_data_1d_raw。",
            stores_market_bars=True,
        ),
        MarketDataStorageRole(
            storage_name="minio",
            display_name="MinIO",
            responsibility="对象归档：原始响应、CSV/Parquet 快照、导入中间产物、报告和模型产物。",
            current_usage="当前本轮 Tushare 日线导入未写归档；后续按批次开启归档。",
            stores_market_bars=False,
        ),
        MarketDataStorageRole(
            storage_name="redis",
            display_name="Redis",
            responsibility="缓存与短期状态：交易日历、证券主数据、查询短缓存和任务锁。",
            current_usage="只保存短期状态，不保存永久业务真相。",
            stores_market_bars=False,
        ),
    ]


def build_ingestion_ledger_response(
    *,
    preview: MarketDataIngestionLedgerPreview,
) -> MarketDataIngestionLedgerResponse:
    has_failed_check = any(check.check_status == "failed" for check in preview.quality_checks)
    has_failed_run = any(run.status == "failed" for run in preview.runs)
    has_review_required_run = any(run.status == "review_required" for run in preview.runs)
    status = "degraded" if has_failed_check or has_failed_run or has_review_required_run else "ok"
    return MarketDataIngestionLedgerResponse(
        status=status,
        generated_at=preview.generated_at,
        persistence_status=preview.persistence_status,
        run_count=preview.run_count,
        quality_check_count=preview.quality_check_count,
        runs=preview.runs,
        quality_checks=preview.quality_checks,
        storage_roles=build_market_data_storage_roles(),
        limitations=[
            *preview.limitations,
            "This BFF endpoint is read-only and does not write PostgreSQL, ClickHouse, or MinIO.",
        ],
    )
