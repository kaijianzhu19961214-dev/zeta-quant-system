from datetime import datetime, timezone
import re

from quant_data_hub.schemas.ingestion_ledger import (
    IngestionLedgerPreviewResponse,
    IngestionQualityCheckRecord,
    IngestionQualityCheckStatus,
    IngestionRunRecord,
    IngestionRunStatus,
)
from quant_data_hub.schemas.source_coverage import MarketDataSourceCoverageItem
from quant_data_hub.services.market_query_service import MarketQueryService


safe_run_id_pattern = re.compile(r"[^A-Za-z0-9_]+")


class IngestionLedgerService:
    def __init__(self, *, market_query_service: MarketQueryService) -> None:
        self.market_query_service = market_query_service

    async def preview_ledger(self, *, limit: int = 100) -> IngestionLedgerPreviewResponse:
        source_coverage = await self.market_query_service.list_source_coverage(limit=limit)
        generated_at = datetime.now(timezone.utc)
        runs = [
            build_ingestion_run_record(coverage=item, generated_at=generated_at)
            for item in source_coverage.coverage
        ]
        quality_checks = [
            check
            for item in source_coverage.coverage
            for check in build_quality_checks(coverage=item)
        ]
        return IngestionLedgerPreviewResponse(
            generated_at=generated_at,
            persistence_status="not_persisted",
            run_count=len(runs),
            quality_check_count=len(quality_checks),
            runs=runs,
            quality_checks=quality_checks,
            limitations=[
                "当前响应由 ClickHouse source coverage 派生，尚未写入 PostgreSQL ingestion_runs / ingestion_quality_checks。",
                "正式落库后应由 quant_data_hub 写 PostgreSQL 控制面，并继续由 ClickHouse 保存行情明细。",
                "MinIO 归档尚未接入本轮 Tushare 日线导入，后续可按 run_id 保存原始响应或 Parquet 快照。",
            ],
        )


def build_ingestion_run_record(
    *,
    coverage: MarketDataSourceCoverageItem,
    generated_at: datetime,
) -> IngestionRunRecord:
    return IngestionRunRecord(
        run_id=build_run_id(coverage=coverage),
        task_type="market_data_ingestion",
        source_name=coverage.source_name,
        dataset_code=coverage.dataset_code,
        timeframe=coverage.timeframe,
        status=resolve_run_status(coverage=coverage),
        storage_target=f"clickhouse:{coverage.storage_object}",
        start_date=coverage.min_date,
        end_date=coverage.max_date,
        row_count=coverage.row_count,
        symbol_count=coverage.symbol_count,
        trading_day_count=coverage.trading_day_count,
        duplicate_key_rows=coverage.duplicate_key_rows,
        output_summary={
            "row_count": coverage.row_count,
            "symbol_count": coverage.symbol_count,
            "trading_day_count": coverage.trading_day_count,
            "duplicate_key_rows": coverage.duplicate_key_rows,
            "storage_object": coverage.storage_object,
        },
        finished_at=generated_at,
    )


def build_quality_checks(*, coverage: MarketDataSourceCoverageItem) -> list[IngestionQualityCheckRecord]:
    run_id = build_run_id(coverage=coverage)
    return [
        IngestionQualityCheckRecord(
            check_id=f"{run_id}_row_count_positive",
            run_id=run_id,
            check_name="row_count_positive",
            check_status=resolve_check_status(condition=coverage.row_count > 0),
            expected_condition="row_count > 0",
            observed_value=str(coverage.row_count),
            details="行情覆盖率必须至少包含一行数据。",
        ),
        IngestionQualityCheckRecord(
            check_id=f"{run_id}_duplicate_key_rows_zero",
            run_id=run_id,
            check_name="duplicate_key_rows_zero",
            check_status=resolve_check_status(condition=coverage.duplicate_key_rows == 0),
            expected_condition="duplicate_key_rows = 0",
            observed_value=str(coverage.duplicate_key_rows),
            details="同一 dataset/source/code/date 或 code/trade_time 不应重复入库。",
        ),
        IngestionQualityCheckRecord(
            check_id=f"{run_id}_date_range_present",
            run_id=run_id,
            check_name="date_range_present",
            check_status=resolve_date_range_status(coverage=coverage),
            expected_condition="min_date and max_date are present",
            observed_value=f"{coverage.min_date or '--'}..{coverage.max_date or '--'}",
            details="导入批次必须有可审计的日期范围。",
        ),
    ]


def build_run_id(*, coverage: MarketDataSourceCoverageItem) -> str:
    raw_run_id = "_".join(
        [
            "ingestion",
            coverage.source_name,
            coverage.dataset_code,
            coverage.timeframe.value,
            str(coverage.min_date or "unknown_start"),
            str(coverage.max_date or "unknown_end"),
        ]
    )
    return safe_run_id_pattern.sub("_", raw_run_id).strip("_")[:128]


def resolve_run_status(*, coverage: MarketDataSourceCoverageItem) -> IngestionRunStatus:
    if coverage.row_count <= 0:
        return "failed"
    if coverage.duplicate_key_rows > 0 or coverage.min_date is None or coverage.max_date is None:
        return "review_required"
    return "succeeded"


def resolve_check_status(*, condition: bool) -> IngestionQualityCheckStatus:
    return "passed" if condition else "failed"


def resolve_date_range_status(*, coverage: MarketDataSourceCoverageItem) -> IngestionQualityCheckStatus:
    if coverage.min_date is not None and coverage.max_date is not None:
        return "passed"
    if coverage.row_count > 0:
        return "warning"
    return "failed"
