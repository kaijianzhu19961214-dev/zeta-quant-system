from collections import defaultdict
from datetime import date
from decimal import Decimal

from quant_contracts import MarketBar


def calculate_forward_returns(
    *,
    bars: list[MarketBar],
    forward_days: int,
) -> dict[tuple[str, date], Decimal]:
    if forward_days < 1:
        raise ValueError("forward_days must be greater than 0")

    bars_by_symbol: dict[str, list[MarketBar]] = defaultdict(list)
    for bar in bars:
        if bar.trade_date is None:
            continue
        bars_by_symbol[bar.symbol].append(bar)

    returns: dict[tuple[str, date], Decimal] = {}
    for symbol, symbol_bars in bars_by_symbol.items():
        sorted_bars = sorted(symbol_bars, key=lambda item: item.trade_date)
        for index, current_bar in enumerate(sorted_bars):
            forward_index = index + forward_days
            if forward_index >= len(sorted_bars):
                continue

            current_close = current_bar.close_price
            forward_close = sorted_bars[forward_index].close_price
            if current_close is None or forward_close is None:
                continue
            if current_close == Decimal("0"):
                continue

            returns[(symbol, current_bar.trade_date)] = forward_close / current_close - Decimal("1")

    return returns
