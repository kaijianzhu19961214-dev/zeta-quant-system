from collections import defaultdict
from datetime import date
from decimal import Decimal

from quant_contracts import FactorDailyValue, FactorGroupReturnPoint


def calculate_group_returns(
    *,
    factor_values: list[FactorDailyValue],
    forward_returns: dict[tuple[str, date], Decimal],
    group_count: int,
) -> list[FactorGroupReturnPoint]:
    if group_count < 2:
        raise ValueError("group_count must be at least 2")

    pairs_by_date: dict[date, list[tuple[float, float]]] = defaultdict(list)
    for factor_value in factor_values:
        if factor_value.factor_value is None:
            continue

        forward_return = forward_returns.get((factor_value.symbol, factor_value.trade_date))
        if forward_return is None:
            continue

        pairs_by_date[factor_value.trade_date].append(
            (float(factor_value.factor_value), float(forward_return))
        )

    points: list[FactorGroupReturnPoint] = []
    for trade_date, pairs in sorted(pairs_by_date.items()):
        points.extend(_calculate_date_group_returns(trade_date=trade_date, pairs=pairs, group_count=group_count))

    return points


def calculate_group_return_spread_mean(*, group_returns: list[FactorGroupReturnPoint]) -> float | None:
    returns_by_date: dict[date, dict[int, float]] = defaultdict(dict)
    for point in group_returns:
        if point.average_forward_return is None:
            continue
        returns_by_date[point.trade_date][point.group_index] = point.average_forward_return

    spreads = [
        group_map[max(group_map)] - group_map[min(group_map)]
        for group_map in returns_by_date.values()
        if len(group_map) >= 2
    ]
    if not spreads:
        return None
    return sum(spreads) / len(spreads)


def _calculate_date_group_returns(
    *,
    trade_date: date,
    pairs: list[tuple[float, float]],
    group_count: int,
) -> list[FactorGroupReturnPoint]:
    if not pairs:
        return []

    grouped_returns: dict[int, list[float]] = defaultdict(list)
    sorted_pairs = sorted(pairs, key=lambda pair: pair[0])
    sample_size = len(sorted_pairs)

    for index, (_, forward_return) in enumerate(sorted_pairs):
        group_index = min(group_count, int(index * group_count / sample_size) + 1)
        grouped_returns[group_index].append(forward_return)

    return [
        FactorGroupReturnPoint(
            trade_date=trade_date,
            group_index=group_index,
            group_count=group_count,
            sample_size=len(group_values),
            average_forward_return=sum(group_values) / len(group_values),
        )
        for group_index, group_values in sorted(grouped_returns.items())
    ]
