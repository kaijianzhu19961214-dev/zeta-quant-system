import unittest

from quant_contracts import MarketBarsQuery, PriceMode, Timeframe
from quant_contracts.mappings import from_legacy_market_bar, to_legacy_market_bars_query


class LegacyMappingTest(unittest.TestCase):
    def test_query_maps_contract_fields_to_legacy_payload(self) -> None:
        query = MarketBarsQuery(
            timeframe=Timeframe.DAY_1,
            symbols=["000001.SZ"],
            start="2026-01-05",
            end="2026-03-13",
            price_mode=PriceMode.HFQ,
            fields=["symbol", "trade_date", "close_price", "volume", "turnover"],
        )

        legacy_payload = to_legacy_market_bars_query(query)

        self.assertEqual(legacy_payload.codes, ["000001.SZ"])
        self.assertEqual(legacy_payload.fields, ["code", "date", "close", "vol", "amount"])
        self.assertEqual(legacy_payload.price_mode, "hfq")

    def test_legacy_row_maps_to_contract_bar(self) -> None:
        bar = from_legacy_market_bar(
            {
                "code": "000001.sz",
                "date": "2026-03-13",
                "open": "10.10",
                "high": "10.30",
                "low": "10.00",
                "close": "10.20",
                "vol": "1000",
                "amount": "10200",
                "ignored": "value",
            }
        )

        self.assertEqual(bar.symbol, "000001.SZ")
        self.assertEqual(str(bar.close_price), "10.20")
        self.assertEqual(str(bar.turnover), "10200")


if __name__ == "__main__":
    unittest.main()

