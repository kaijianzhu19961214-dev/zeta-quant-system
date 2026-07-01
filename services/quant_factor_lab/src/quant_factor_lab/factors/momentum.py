from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from quant_contracts import AssetClass, FactorDailyValue, FactorFamily, FactorMode, MarketBar


def calculate_momentum_factor(
    *,
    bars: Sequence[MarketBar],
    factor_name: str,
    lookback_window: int,
    universe_name: str,
    data_source: str,
    data_version: str | None,
    factor_version: str,
    run_id: str | None,
    asset_class: AssetClass = AssetClass.EQUITY,
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL,
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME,
) -> list[FactorDailyValue]:
    if lookback_window < 1:
        raise ValueError("lookback_window must be greater than 0")

    bars_by_symbol = _group_daily_bars_by_symbol(bars)
    values: list[FactorDailyValue] = []

    for symbol, symbol_bars in sorted(bars_by_symbol.items()):
        for index, current_bar in enumerate(symbol_bars):
            current_trade_date = _get_trade_date(current_bar)
            if current_trade_date is None:
                continue

            factor_value = None
            if index >= lookback_window:
                previous_bar = symbol_bars[index - lookback_window]
                factor_value = _calculate_return(
                    current_close=current_bar.close_price,
                    previous_close=previous_bar.close_price,
                )

            values.append(
                FactorDailyValue(
                    symbol=symbol,
                    trade_date=current_trade_date,
                    factor_name=factor_name,
                    factor_value=factor_value,
                    asset_class=asset_class,
                    factor_mode=factor_mode,
                    factor_family=factor_family,
                    universe_name=universe_name,
                    data_source=data_source,
                    data_version=data_version,
                    factor_version=factor_version,
                    run_id=run_id,
                )
            )

    return values


def _group_daily_bars_by_symbol(bars: Sequence[MarketBar]) -> dict[str, list[MarketBar]]:
    bars_by_symbol: dict[str, list[MarketBar]] = defaultdict(list)
    for bar in bars:
        if bar.trade_date is None:
            continue
        bars_by_symbol[bar.symbol].append(bar)

    for symbol, symbol_bars in bars_by_symbol.items():
        bars_by_symbol[symbol] = sorted(symbol_bars, key=_sort_key)

    return dict(bars_by_symbol)


def _sort_key(bar: MarketBar) -> tuple[date, str]:
    trade_date = _get_trade_date(bar)
    if trade_date is None:
        raise ValueError("daily market bar requires trade_date")
    return (trade_date, bar.symbol)


def _get_trade_date(bar: MarketBar) -> date | None:
    if bar.trade_date:
        return bar.trade_date
    if bar.trade_time:
        return bar.trade_time.date()
    return None


def _calculate_return(*, current_close: Decimal | None, previous_close: Decimal | None) -> Decimal | None:
    if current_close is None:
        return None
    if previous_close is None:
        return None
    if previous_close == Decimal("0"):
        return None
    return current_close / previous_close - Decimal("1")
