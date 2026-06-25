import unittest

from pydantic import ValidationError
from quant_contracts import FactorCalculationRequest, FactorDailyValue, PriceMode, Timeframe


class FactorSchemaTest(unittest.TestCase):
    def test_should_normalize_factor_request_when_payload_is_valid(self) -> None:
        request = FactorCalculationRequest(
            factor_name="Momentum_20D",
            symbols=[" 000001.sz ", "000651.SZ"],
            start="2026-01-01",
            end="2026-03-13",
        )

        self.assertEqual(request.factor_name, "momentum_20d")
        self.assertEqual(request.symbols, ["000001.SZ", "000651.SZ"])
        self.assertEqual(request.timeframe, Timeframe.DAY_1)

    def test_should_reject_non_daily_timeframe_for_mvp_factor_request(self) -> None:
        with self.assertRaises(ValidationError):
            FactorCalculationRequest(
                factor_name="momentum_20d",
                symbols=["000001.SZ"],
                start="2026-01-01",
                end="2026-03-13",
                timeframe=Timeframe.MINUTE_1,
            )

    def test_should_require_batch_id_when_qfq_price_mode_is_used(self) -> None:
        with self.assertRaises(ValidationError):
            FactorCalculationRequest(
                factor_name="momentum_20d",
                symbols=["000001.SZ"],
                start="2026-01-01",
                end="2026-03-13",
                price_mode=PriceMode.QFQ,
            )

    def test_should_normalize_factor_daily_value_symbol(self) -> None:
        value = FactorDailyValue(
            symbol=" 000001.sz ",
            trade_date="2026-03-13",
            factor_name="momentum_20d",
            factor_value="0.15",
        )

        self.assertEqual(value.symbol, "000001.SZ")
        self.assertEqual(str(value.factor_value), "0.15")


if __name__ == "__main__":
    unittest.main()
