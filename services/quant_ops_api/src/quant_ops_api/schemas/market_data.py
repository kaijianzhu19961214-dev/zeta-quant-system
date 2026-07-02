from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator
from quant_contracts import MarketBar, MarketBarsMeta


PriceModeName = Literal["raw", "qfq", "hfq"]
MarketDataServiceStatus = Literal["ok", "degraded"]
TimeframeName = Literal["1m", "5m", "1d"]
StorageRoleName = Literal["postgresql", "clickhouse", "minio", "redis"]


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
