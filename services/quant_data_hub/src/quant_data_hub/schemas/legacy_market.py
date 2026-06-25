from datetime import date, datetime

from pydantic import Field, field_validator, model_validator
from quant_contracts import MarketBarsQuery, PriceMode, Timeframe
from quant_contracts.mappings.legacy_market_data import LEGACY_TO_CONTRACT_FIELD_NAMES
from quant_contracts.schemas.common import ContractModel


class LegacyMarketBarsQueryRequest(ContractModel):
    timeframe: Timeframe
    codes: list[str] = Field(min_length=1, max_length=500)
    start: date | datetime | str
    end: date | datetime | str
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    fields: list[str] | None = None
    limit: int = Field(default=10000, ge=1, le=100000)

    @field_validator("codes")
    @classmethod
    def normalize_codes(cls, values: list[str]) -> list[str]:
        normalized_values = [value.strip().upper() for value in values if value.strip()]
        if not normalized_values:
            raise ValueError("codes must not be empty")
        return normalized_values

    @field_validator("fields")
    @classmethod
    def normalize_fields(cls, values: list[str] | None) -> list[str] | None:
        if values is None:
            return None

        normalized_values = [value.strip() for value in values if value.strip()]
        return normalized_values or None

    @model_validator(mode="after")
    def validate_price_mode_requirements(self) -> "LegacyMarketBarsQueryRequest":
        if self.price_mode != PriceMode.QFQ:
            return self
        if self.batch_id:
            return self
        raise ValueError("batch_id is required when price_mode=qfq")

    def to_contract_query(self) -> MarketBarsQuery:
        contract_fields = None
        if self.fields:
            contract_fields = [
                LEGACY_TO_CONTRACT_FIELD_NAMES.get(field_name, field_name)
                for field_name in self.fields
            ]

        return MarketBarsQuery(
            timeframe=self.timeframe,
            symbols=self.codes,
            start=self.start,
            end=self.end,
            price_mode=self.price_mode,
            dataset_code=self.dataset_code,
            batch_id=self.batch_id,
            fields=contract_fields,
            limit=self.limit,
        )

