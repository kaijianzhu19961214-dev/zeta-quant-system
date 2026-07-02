from datetime import date, datetime, timezone

from pydantic import Field
from quant_contracts import Timeframe
from quant_contracts.schemas.common import ContractModel


class MarketDataSourceCoverageItem(ContractModel):
    timeframe: Timeframe
    storage_object: str = Field(min_length=1, max_length=128)
    dataset_code: str = Field(min_length=1, max_length=128)
    source_name: str = Field(min_length=1, max_length=128)
    row_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    trading_day_count: int = Field(ge=0)
    min_date: date | None = None
    max_date: date | None = None
    duplicate_key_rows: int = Field(ge=0)


class MarketDataSourceCoverageResponse(ContractModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    row_count: int = Field(ge=0)
    coverage: list[MarketDataSourceCoverageItem] = Field(default_factory=list)
