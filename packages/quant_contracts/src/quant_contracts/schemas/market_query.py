from datetime import date, datetime

from pydantic import Field, field_validator, model_validator

from quant_contracts.enums import PriceMode, Timeframe
from quant_contracts.schemas.common import ContractModel
from quant_contracts.schemas.market_data import MarketBar


class MarketBarsQuery(ContractModel):
    timeframe: Timeframe
    symbols: list[str] = Field(min_length=1, max_length=500)
    start: date | datetime | str
    end: date | datetime | str
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    fields: list[str] | None = None
    limit: int = Field(default=10000, ge=1, le=100000)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not normalized_symbols:
            raise ValueError("symbols must not be empty")
        return normalized_symbols

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value

        normalized_fields = []
        for field_name in value:
            normalized_field = field_name.strip()
            if normalized_field and normalized_field not in normalized_fields:
                normalized_fields.append(normalized_field)

        return normalized_fields or None

    @model_validator(mode="after")
    def validate_price_mode_requirements(self) -> "MarketBarsQuery":
        if self.price_mode != PriceMode.QFQ:
            return self
        if self.batch_id:
            return self
        raise ValueError("batch_id is required when price_mode is qfq")


class MarketBarsMeta(ContractModel):
    timeframe: Timeframe
    price_mode: PriceMode = PriceMode.RAW
    row_count: int = Field(default=0, ge=0)
    dataset_code: str | None = None
    batch_id: str | None = None


class MarketBarsResponse(ContractModel):
    meta: MarketBarsMeta
    rows: list[MarketBar] = Field(default_factory=list)

