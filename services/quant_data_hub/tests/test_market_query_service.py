import unittest
from typing import Any

from quant_contracts import MarketBarsQuery, PriceMode, Timeframe
from quant_data_hub.services.market_query_service import MarketQueryService


class FakeClickHouseReader:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.payload = payload or {"data": []}
        self.queries: list[str] = []

    async def query_json(self, query: str, *, timeout_seconds: int = 120) -> dict[str, Any]:
        self.queries.append(query)
        return self.payload


class MarketQueryServiceTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.reader = FakeClickHouseReader()
        self.service = MarketQueryService(reader=self.reader, database="quant_market")

    def test_should_build_raw_1m_query_with_contract_fields(self) -> None:
        request = MarketBarsQuery(
            timeframe=Timeframe.MINUTE_1,
            symbols=["000001.SZ"],
            start="2026-03-13 09:30:00",
            end="2026-03-13 15:00:00",
            price_mode=PriceMode.RAW,
            fields=["symbol", "trade_time", "close_price", "volume"],
            limit=100,
        )

        query = self.service.build_bars_query(request)

        self.assertIn("FROM quant_market.market_data_1m_raw AS r", query)
        self.assertIn("r.close AS close_price", query)
        self.assertIn("r.vol AS volume", query)
        self.assertIn("r.code IN ('000001.SZ')", query)
        self.assertIn("LIMIT 100", query)

    def test_should_build_qfq_1d_query_with_raw_join(self) -> None:
        request = MarketBarsQuery(
            timeframe=Timeframe.DAY_1,
            symbols=["000001.SZ"],
            start="2026-01-05",
            end="2026-03-13",
            price_mode=PriceMode.QFQ,
            batch_id="qfq_20260313",
            fields=["symbol", "trade_date", "close_price", "volume"],
        )

        query = self.service.build_bars_query(request)

        self.assertIn("FROM quant_market.market_data_1d_qfq_cache AS q", query)
        self.assertIn("ANY LEFT JOIN quant_market.market_data_1d_raw AS r", query)
        self.assertIn("q.qfq_close AS close_price", query)
        self.assertIn("r.vol AS volume", query)
        self.assertIn("q.batch_id = 'qfq_20260313'", query)

    def test_should_reject_unsupported_field_when_building_query(self) -> None:
        request = MarketBarsQuery(
            timeframe=Timeframe.MINUTE_1,
            symbols=["000001.SZ"],
            start="2026-03-13",
            end="2026-03-13",
            fields=["symbol", "drop table"],
        )

        with self.assertRaises(ValueError):
            self.service.build_bars_query(request)

    def test_should_reject_unsafe_symbol_when_building_query(self) -> None:
        request = MarketBarsQuery(
            timeframe=Timeframe.MINUTE_1,
            symbols=["000001.SZ';DROP"],
            start="2026-03-13",
            end="2026-03-13",
        )

        with self.assertRaises(ValueError):
            self.service.build_bars_query(request)

    async def test_should_return_contract_response_when_reader_returns_rows(self) -> None:
        reader = FakeClickHouseReader(
            {
                "data": [
                    {
                        "symbol": "000001.SZ",
                        "trade_date": "2026-03-13",
                        "close_price": "10.20",
                        "volume": "1000",
                        "turnover": "10200",
                    }
                ]
            }
        )
        service = MarketQueryService(reader=reader, database="quant_market")
        request = MarketBarsQuery(
            timeframe=Timeframe.DAY_1,
            symbols=["000001.SZ"],
            start="2026-03-13",
            end="2026-03-13",
            fields=["symbol", "trade_date", "close_price", "volume", "turnover"],
        )

        response = await service.query_bars(request)

        self.assertEqual(response.meta.row_count, 1)
        self.assertEqual(response.rows[0].symbol, "000001.SZ")
        self.assertEqual(str(response.rows[0].close_price), "10.20")


if __name__ == "__main__":
    unittest.main()

