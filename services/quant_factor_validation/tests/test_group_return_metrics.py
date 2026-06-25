from datetime import date
from decimal import Decimal
import unittest

from quant_contracts import FactorDailyValue
from quant_factor_validation.metrics import (
    calculate_group_return_spread_mean,
    calculate_group_returns,
)


class GroupReturnMetricsTest(unittest.TestCase):
    def test_should_calculate_group_returns_by_factor_order(self) -> None:
        group_returns = calculate_group_returns(
            factor_values=[
                _make_factor_value(symbol="000001.SZ", factor_value="0.1"),
                _make_factor_value(symbol="000002.SZ", factor_value="0.2"),
                _make_factor_value(symbol="000003.SZ", factor_value="0.3"),
            ],
            forward_returns={
                ("000001.SZ", date(2026, 3, 13)): Decimal("0.01"),
                ("000002.SZ", date(2026, 3, 13)): Decimal("0.03"),
                ("000003.SZ", date(2026, 3, 13)): Decimal("0.05"),
            },
            group_count=3,
        )

        self.assertEqual(len(group_returns), 3)
        self.assertEqual(group_returns[0].group_index, 1)
        self.assertAlmostEqual(group_returns[0].average_forward_return, 0.01)
        self.assertEqual(group_returns[2].group_index, 3)
        self.assertAlmostEqual(
            calculate_group_return_spread_mean(group_returns=group_returns),
            0.04,
        )

    def test_should_ignore_missing_factor_values_and_returns(self) -> None:
        group_returns = calculate_group_returns(
            factor_values=[
                _make_factor_value(symbol="000001.SZ", factor_value="0.1"),
                _make_factor_value(symbol="000002.SZ", factor_value=None),
                _make_factor_value(symbol="000003.SZ", factor_value="0.3"),
            ],
            forward_returns={
                ("000001.SZ", date(2026, 3, 13)): Decimal("0.01"),
            },
            group_count=3,
        )

        self.assertEqual(len(group_returns), 1)
        self.assertEqual(group_returns[0].sample_size, 1)
        self.assertIsNone(calculate_group_return_spread_mean(group_returns=group_returns))

    def test_should_raise_error_when_group_count_is_invalid(self) -> None:
        with self.assertRaises(ValueError):
            calculate_group_returns(factor_values=[], forward_returns={}, group_count=1)


def _make_factor_value(*, symbol: str, factor_value: str | None) -> FactorDailyValue:
    return FactorDailyValue(
        symbol=symbol,
        trade_date="2026-03-13",
        factor_name="momentum_1d",
        factor_value=factor_value,
    )


if __name__ == "__main__":
    unittest.main()
