import unittest
from datetime import date

from pydantic import ValidationError

from quant_contracts import MarketBar, MarketBarsQuery, PriceMode, Timeframe


class MarketQueryTest(unittest.TestCase):
    def test_query_normalizes_symbols_and_deduplicates_fields(self) -> None:
        query = MarketBarsQuery(
            timeframe=Timeframe.DAY_1,
            symbols=[" 000001.sz ", "000651.SZ"],
            start=date(2026, 1, 5),
            end=date(2026, 3, 13),
            fields=["symbol", "close_price", "close_price"],
        )

        self.assertEqual(query.symbols, ["000001.SZ", "000651.SZ"])
        self.assertEqual(query.fields, ["symbol", "close_price"])

    def test_qfq_requires_batch_id(self) -> None:
        with self.assertRaises(ValidationError):
            MarketBarsQuery(
                timeframe=Timeframe.DAY_1,
                symbols=["000001.SZ"],
                start="2026-01-05",
                end="2026-03-13",
                price_mode=PriceMode.QFQ,
            )

    def test_market_bar_requires_trade_date_or_trade_time(self) -> None:
        with self.assertRaises(ValidationError):
            MarketBar(symbol="000001.SZ", close_price="10.50")


if __name__ == "__main__":
    unittest.main()

