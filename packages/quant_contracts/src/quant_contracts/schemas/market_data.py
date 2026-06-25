from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from quant_contracts.schemas.common import ContractModel


class MarketBar(ContractModel):
    symbol: str = Field(min_length=1, max_length=32)
    trade_date: date | None = None
    trade_time: datetime | None = None
    open_price: Decimal | None = Field(default=None, ge=0)
    high_price: Decimal | None = Field(default=None, ge=0)
    low_price: Decimal | None = Field(default=None, ge=0)
    close_price: Decimal | None = Field(default=None, ge=0)
    pre_close_price: Decimal | None = Field(default=None, ge=0)
    change_value: Decimal | None = None
    pct_change: Decimal | None = None
    volume: Decimal | None = Field(default=None, ge=0)
    turnover: Decimal | None = Field(default=None, ge=0)
    vwap: Decimal | None = Field(default=None, ge=0)
    adjustment_factor: Decimal | None = Field(default=None, ge=0)
    source_name: str | None = Field(default=None, max_length=128)
    created_at: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized_value = value.strip().upper()
        if not normalized_value:
            raise ValueError("symbol must not be blank")
        return normalized_value

    @model_validator(mode="after")
    def validate_time_key(self) -> "MarketBar":
        if self.trade_date or self.trade_time:
            return self
        raise ValueError("trade_date or trade_time is required")

