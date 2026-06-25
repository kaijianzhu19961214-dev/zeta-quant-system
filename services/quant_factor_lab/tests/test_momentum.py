import unittest

from quant_contracts import MarketBar
from quant_factor_lab.factors import calculate_momentum_factor


class MomentumFactorTest(unittest.TestCase):
    def test_should_calculate_momentum_without_using_future_prices(self) -> None:
        rows = calculate_momentum_factor(
            bars=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-11", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-12", close_price="11"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="15"),
            ],
            factor_name="momentum_2d",
            lookback_window=2,
            universe_name="default",
            data_source="unit_test",
            data_version="fixture_v1",
            factor_version="v1",
            run_id="run_test",
        )

        self.assertIsNone(rows[0].factor_value)
        self.assertIsNone(rows[1].factor_value)
        self.assertEqual(str(rows[2].factor_value), "0.5")
        self.assertEqual(rows[2].run_id, "run_test")

    def test_should_return_none_when_previous_close_is_zero(self) -> None:
        rows = calculate_momentum_factor(
            bars=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-12", close_price="0"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="15"),
            ],
            factor_name="momentum_1d",
            lookback_window=1,
            universe_name="default",
            data_source="unit_test",
            data_version=None,
            factor_version="v1",
            run_id=None,
        )

        self.assertIsNone(rows[1].factor_value)


if __name__ == "__main__":
    unittest.main()
