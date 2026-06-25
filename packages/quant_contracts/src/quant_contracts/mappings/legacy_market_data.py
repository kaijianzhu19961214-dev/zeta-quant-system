from typing import Any, Mapping

from quant_contracts.schemas.common import ContractModel
from quant_contracts.schemas.market_data import MarketBar
from quant_contracts.schemas.market_query import MarketBarsQuery


CONTRACT_TO_LEGACY_FIELD_NAMES = {
    "symbol": "code",
    "trade_date": "date",
    "trade_time": "trade_time",
    "open_price": "open",
    "high_price": "high",
    "low_price": "low",
    "close_price": "close",
    "pre_close_price": "pre_close",
    "change_value": "change",
    "pct_change": "pct_chg",
    "volume": "vol",
    "turnover": "amount",
    "vwap": "vwap",
    "adjustment_factor": "adj_factor",
    "source_name": "source_name",
    "created_at": "created_at",
}

LEGACY_TO_CONTRACT_FIELD_NAMES = {
    legacy_field: contract_field
    for contract_field, legacy_field in CONTRACT_TO_LEGACY_FIELD_NAMES.items()
}

LEGACY_TO_CONTRACT_FIELD_NAMES.update(
    {
        "qfq_open": "open_price",
        "qfq_high": "high_price",
        "qfq_low": "low_price",
        "qfq_close": "close_price",
        "qfq_factor": "adjustment_factor",
        "hfq_open": "open_price",
        "hfq_high": "high_price",
        "hfq_low": "low_price",
        "hfq_close": "close_price",
        "hfq_factor": "adjustment_factor",
    }
)


class LegacyMarketBarsQueryPayload(ContractModel):
    timeframe: str
    codes: list[str]
    start: str
    end: str
    price_mode: str
    dataset_code: str | None = None
    batch_id: str | None = None
    fields: list[str] | None = None
    limit: int


def to_legacy_market_bars_query(query: MarketBarsQuery) -> LegacyMarketBarsQueryPayload:
    legacy_fields = None
    if query.fields:
        legacy_fields = [
            CONTRACT_TO_LEGACY_FIELD_NAMES.get(field_name, field_name)
            for field_name in query.fields
        ]

    return LegacyMarketBarsQueryPayload(
        timeframe=query.timeframe.value,
        codes=query.symbols,
        start=str(query.start),
        end=str(query.end),
        price_mode=query.price_mode.value,
        dataset_code=query.dataset_code,
        batch_id=query.batch_id,
        fields=legacy_fields,
        limit=query.limit,
    )


def from_legacy_market_bar(row: Mapping[str, Any]) -> MarketBar:
    contract_row = {}
    for legacy_field, value in row.items():
        contract_field = LEGACY_TO_CONTRACT_FIELD_NAMES.get(legacy_field)
        if not contract_field:
            continue
        contract_row[contract_field] = value

    return MarketBar.model_validate(contract_row)

