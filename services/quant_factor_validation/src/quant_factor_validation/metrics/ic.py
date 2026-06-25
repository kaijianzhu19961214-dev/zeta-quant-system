from collections import defaultdict
from datetime import date
from decimal import Decimal
from math import sqrt

from quant_contracts import FactorDailyValue, FactorIcPoint


def calculate_ic_series(
    *,
    factor_values: list[FactorDailyValue],
    forward_returns: dict[tuple[str, date], Decimal],
) -> list[FactorIcPoint]:
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

    points: list[FactorIcPoint] = []
    for trade_date, pairs in sorted(pairs_by_date.items()):
        factor_series = [pair[0] for pair in pairs]
        return_series = [pair[1] for pair in pairs]
        points.append(
            FactorIcPoint(
                trade_date=trade_date,
                sample_size=len(pairs),
                ic=pearson_correlation(factor_series, return_series),
                rank_ic=spearman_correlation(factor_series, return_series),
            )
        )

    return points


def pearson_correlation(left: list[float], right: list[float]) -> float | None:
    if len(left) != len(right):
        raise ValueError("series length mismatch")
    if len(left) < 2:
        return None

    left_mean = sum(left) / len(left)
    right_mean = sum(right) / len(right)
    numerator = sum((left_value - left_mean) * (right_value - right_mean) for left_value, right_value in zip(left, right))
    left_variance = sum((left_value - left_mean) ** 2 for left_value in left)
    right_variance = sum((right_value - right_mean) ** 2 for right_value in right)
    denominator = sqrt(left_variance * right_variance)
    if denominator == 0:
        return None

    return numerator / denominator


def spearman_correlation(left: list[float], right: list[float]) -> float | None:
    return pearson_correlation(rank_values(left), rank_values(right))


def rank_values(values: list[float]) -> list[float]:
    sorted_values = sorted((value, index) for index, value in enumerate(values))
    ranks = [0.0] * len(values)
    cursor = 0

    while cursor < len(sorted_values):
        end = cursor
        while end < len(sorted_values) and sorted_values[end][0] == sorted_values[cursor][0]:
            end += 1

        average_rank = (cursor + 1 + end) / 2
        for _, original_index in sorted_values[cursor:end]:
            ranks[original_index] = average_rank

        cursor = end

    return ranks


def mean_optional(values: list[float | None]) -> float | None:
    valid_values = [value for value in values if value is not None]
    if not valid_values:
        return None
    return sum(valid_values) / len(valid_values)


def standard_deviation(values: list[float | None]) -> float | None:
    valid_values = [value for value in values if value is not None]
    if len(valid_values) < 2:
        return None

    value_mean = sum(valid_values) / len(valid_values)
    variance = sum((value - value_mean) ** 2 for value in valid_values) / (len(valid_values) - 1)
    return sqrt(variance)
