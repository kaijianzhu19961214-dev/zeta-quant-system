import re

from quant_contracts import (
    FactorCalculationMeta,
    FactorCalculationRequest,
    FactorCalculationResponse,
    MarketBarsQuery,
)

from quant_factor_lab.factors import calculate_momentum_factor
from quant_factor_lab.repositories.market_data_reader import MarketDataReader

MOMENTUM_FACTOR_PATTERN = re.compile(r"^momentum_(?P<window>[1-9][0-9]*)d$")


class FactorCalculationService:
    def __init__(self, *, market_data_reader: MarketDataReader) -> None:
        self.market_data_reader = market_data_reader

    async def calculate(self, *, request: FactorCalculationRequest) -> FactorCalculationResponse:
        lookback_window = _resolve_momentum_window(request.factor_name)
        if request.lookback_window != lookback_window:
            raise ValueError("lookback_window must match the window encoded in factor_name")

        market_response = await self.market_data_reader.query_bars(
            query=MarketBarsQuery(
                timeframe=request.timeframe,
                symbols=request.symbols,
                start=request.start,
                end=request.end,
                price_mode=request.price_mode,
                dataset_code=request.dataset_code,
                batch_id=request.batch_id,
                fields=["symbol", "trade_date", "close_price", "volume", "turnover"],
                limit=request.limit,
            )
        )

        values = calculate_momentum_factor(
            bars=market_response.rows,
            factor_name=request.factor_name,
            lookback_window=lookback_window,
            universe_name=request.universe_name,
            data_source=request.data_source,
            data_version=request.data_version,
            factor_version=request.factor_version,
            run_id=request.run_id,
        )

        return FactorCalculationResponse(
            meta=FactorCalculationMeta(
                factor_name=request.factor_name,
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                row_count=len(values),
                lookback_window=lookback_window,
                universe_name=request.universe_name,
                data_source=request.data_source,
                data_version=request.data_version,
                factor_version=request.factor_version,
                run_id=request.run_id,
                dataset_code=request.dataset_code or market_response.meta.dataset_code,
                batch_id=request.batch_id or market_response.meta.batch_id,
            ),
            rows=values,
        )


def _resolve_momentum_window(factor_name: str) -> int:
    match = MOMENTUM_FACTOR_PATTERN.fullmatch(factor_name)
    if not match:
        raise ValueError("only momentum_*d factors are supported in MVP")

    window = int(match.group("window"))
    if window <= 252:
        return window
    raise ValueError("momentum window must be less than or equal to 252")
