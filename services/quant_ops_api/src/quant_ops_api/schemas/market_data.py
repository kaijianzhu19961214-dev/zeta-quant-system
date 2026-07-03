from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from quant_contracts import MarketBar, MarketBarsMeta


PriceModeName = Literal["raw", "qfq", "hfq"]
MarketDataServiceStatus = Literal["ok", "degraded"]
TimeframeName = Literal["1m", "5m", "1d"]
StorageRoleName = Literal["postgresql", "clickhouse", "minio", "redis"]
IngestionPersistenceStatus = Literal["not_persisted", "persisted"]
IngestionRunStatus = Literal["succeeded", "review_required", "failed"]
IngestionQualityCheckStatus = Literal["passed", "warning", "failed"]


class QfqBatchSummary(BaseModel):
    batch_id: str = Field(min_length=1, max_length=128)
    qfq_base_date: date
    status: str = Field(min_length=1, max_length=64)
    description: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None


class MarketPriceModeStatus(BaseModel):
    price_mode: PriceModeName
    display_name: str = Field(min_length=1, max_length=64)
    storage_object: str = Field(min_length=1, max_length=128)
    source_relation: str = Field(min_length=1, max_length=256)
    requires_batch_id: bool
    available: bool
    latest_batch_id: str | None = None
    latest_qfq_base_date: date | None = None


class MarketDataPriceModeOverview(BaseModel):
    status: MarketDataServiceStatus
    generated_at: datetime
    qfq_batch_count: int = Field(ge=0)
    latest_qfq_batch: QfqBatchSummary | None = None
    price_modes: list[MarketPriceModeStatus] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MarketDataSourceCoverageItem(BaseModel):
    timeframe: TimeframeName
    storage_object: str = Field(min_length=1, max_length=128)
    dataset_code: str = Field(min_length=1, max_length=128)
    source_name: str = Field(min_length=1, max_length=128)
    row_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    trading_day_count: int = Field(ge=0)
    min_date: date | None = None
    max_date: date | None = None
    duplicate_key_rows: int = Field(ge=0)


class MarketDataStorageRole(BaseModel):
    storage_name: StorageRoleName
    display_name: str = Field(min_length=1, max_length=64)
    responsibility: str = Field(min_length=1, max_length=256)
    current_usage: str = Field(min_length=1, max_length=256)
    stores_market_bars: bool


class MarketDataSourceCoverageResponse(BaseModel):
    status: MarketDataServiceStatus
    generated_at: datetime
    row_count: int = Field(ge=0)
    coverage: list[MarketDataSourceCoverageItem] = Field(default_factory=list)
    storage_roles: list[MarketDataStorageRole] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MarketDataIngestionRunRecord(BaseModel):
    run_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=64)
    source_name: str = Field(min_length=1, max_length=128)
    dataset_code: str = Field(min_length=1, max_length=128)
    timeframe: TimeframeName
    status: IngestionRunStatus
    storage_target: str = Field(min_length=1, max_length=128)
    start_date: date | None = None
    end_date: date | None = None
    row_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    trading_day_count: int = Field(ge=0)
    duplicate_key_rows: int = Field(ge=0)
    output_summary: dict[str, int | str | None] = Field(default_factory=dict)
    finished_at: datetime | None = None


class MarketDataIngestionQualityCheckRecord(BaseModel):
    check_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    check_name: str = Field(min_length=1, max_length=128)
    check_status: IngestionQualityCheckStatus
    expected_condition: str = Field(min_length=1, max_length=256)
    observed_value: str | None = None
    details: str | None = None


class MarketDataIngestionLedgerPreview(BaseModel):
    generated_at: datetime
    persistence_status: IngestionPersistenceStatus
    run_count: int = Field(ge=0)
    quality_check_count: int = Field(ge=0)
    runs: list[MarketDataIngestionRunRecord] = Field(default_factory=list)
    quality_checks: list[MarketDataIngestionQualityCheckRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class MarketDataIngestionLedgerResponse(MarketDataIngestionLedgerPreview):
    status: MarketDataServiceStatus
    storage_roles: list[MarketDataStorageRole] = Field(default_factory=list)


class MarketDataBarsSampleRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    timeframe: TimeframeName = "1d"
    start: str = Field(min_length=1, max_length=32)
    end: str = Field(min_length=1, max_length=32)
    price_mode: PriceModeName = "raw"
    batch_id: str | None = Field(default=None, max_length=128)
    fields: list[str] | None = None
    limit: int = Field(default=5, ge=1, le=20)

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("start", "end")
    @classmethod
    def normalize_bound(cls, value: str) -> str:
        return value.strip()

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None

        normalized_fields: list[str] = []
        for field_name in value:
            normalized_field = field_name.strip()
            if normalized_field and normalized_field not in normalized_fields:
                normalized_fields.append(normalized_field)
        return normalized_fields or None


class MarketDataBarsSampleResponse(BaseModel):
    generated_at: datetime
    request: MarketDataBarsSampleRequest
    meta: MarketBarsMeta
    rows: list[MarketBar] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
