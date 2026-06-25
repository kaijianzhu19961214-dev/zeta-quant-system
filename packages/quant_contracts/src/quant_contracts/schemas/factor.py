from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from quant_contracts.enums import PriceMode, Timeframe
from quant_contracts.schemas.common import ContractModel


class FactorCalculationRequest(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    symbols: list[str] = Field(min_length=1, max_length=500)
    start: date | str
    end: date | str
    timeframe: Timeframe = Timeframe.DAY_1
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    lookback_window: int = Field(default=20, ge=1, le=252)
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    data_source: str = Field(default="quant_data_hub", min_length=1, max_length=64)
    data_version: str | None = Field(default=None, max_length=128)
    factor_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=100000, ge=1, le=500000)

    @field_validator("factor_name", "universe_name", "data_source", "factor_version", "run_id")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("factor_name")
    @classmethod
    def validate_factor_name(cls, value: str) -> str:
        if value.replace("_", "").isalnum() and value[0].isalpha():
            return value.lower()
        raise ValueError("factor_name must use lowercase letters, numbers, and underscores")

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not normalized_symbols:
            raise ValueError("symbols must not be empty")
        return normalized_symbols

    @model_validator(mode="after")
    def validate_daily_factor_request(self) -> "FactorCalculationRequest":
        if self.timeframe != Timeframe.DAY_1:
            raise ValueError("MVP factor calculation only supports 1d timeframe")
        if self.price_mode != PriceMode.QFQ:
            return self
        if self.batch_id:
            return self
        raise ValueError("batch_id is required when price_mode is qfq")


class FactorDailyValue(ContractModel):
    symbol: str = Field(min_length=1, max_length=32)
    trade_date: date
    factor_name: str = Field(min_length=1, max_length=128)
    factor_value: Decimal | None = None
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    data_source: str = Field(default="quant_data_hub", min_length=1, max_length=64)
    data_version: str | None = Field(default=None, max_length=128)
    factor_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    created_at: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized_value = value.strip().upper()
        if normalized_value:
            return normalized_value
        raise ValueError("symbol must not be blank")


class FactorCalculationMeta(ContractModel):
    factor_name: str
    timeframe: Timeframe
    price_mode: PriceMode
    row_count: int = Field(ge=0)
    lookback_window: int = Field(ge=1)
    universe_name: str
    data_source: str
    data_version: str | None = None
    factor_version: str
    run_id: str | None = None
    dataset_code: str | None = None
    batch_id: str | None = None


class FactorCalculationResponse(ContractModel):
    meta: FactorCalculationMeta
    rows: list[FactorDailyValue] = Field(default_factory=list)
