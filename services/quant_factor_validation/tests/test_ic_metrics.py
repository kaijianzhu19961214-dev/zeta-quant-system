import unittest
from decimal import Decimal

from quant_contracts import FactorDailyValue
from quant_factor_validation.metrics import calculate_ic_series
from quant_factor_validation.metrics.forward_return import calculate_forward_returns
from quant_factor_validation.metrics.ic import pearson_correlation, rank_values, spearman_correlation
from quant_contracts import MarketBar


class IcMetricsTest(unittest.TestCase):
    def test_should_calculate_pearson_and_spearman_correlation(self) -> None:
        self.assertAlmostEqual(pearson_correlation([1.0, 2.0, 3.0], [1.0, 2.0, 4.0]), 0.9819805061)
        self.assertEqual(spearman_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0]), -1.0)
        self.assertEqual(rank_values([10.0, 10.0, 30.0]), [1.5, 1.5, 3.0])

    def test_should_calculate_ic_series_by_trade_date(self) -> None:
        factor_values = [
            FactorDailyValue(symbol="000001.SZ", trade_date="2026-03-13", factor_name="momentum_1d", factor_value="0.10"),
            FactorDailyValue(symbol="000002.SZ", trade_date="2026-03-13", factor_name="momentum_1d", factor_value="0.20"),
            FactorDailyValue(symbol="000003.SZ", trade_date="2026-03-13", factor_name="momentum_1d", factor_value="0.30"),
        ]
        forward_returns = {
            ("000001.SZ", factor_values[0].trade_date): Decimal("0.01"),
            ("000002.SZ", factor_values[1].trade_date): Decimal("0.02"),
            ("000003.SZ", factor_values[2].trade_date): Decimal("0.03"),
        }

        points = calculate_ic_series(factor_values=factor_values, forward_returns=forward_returns)

        self.assertEqual(points[0].sample_size, 3)
        self.assertEqual(points[0].ic, 1.0)
        self.assertEqual(points[0].rank_ic, 1.0)

    def test_should_calculate_forward_returns_without_current_day_leakage(self) -> None:
        returns = calculate_forward_returns(
            bars=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-16", close_price="12"),
            ],
            forward_days=1,
        )

        self.assertEqual(str(returns[("000001.SZ", factor_values_date("2026-03-13"))]), "0.2")


def factor_values_date(value: str):
    return FactorDailyValue(symbol="000001.SZ", trade_date=value, factor_name="momentum_1d").trade_date


if __name__ == "__main__":
    unittest.main()
