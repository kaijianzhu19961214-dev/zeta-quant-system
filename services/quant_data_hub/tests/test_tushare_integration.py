import unittest
from decimal import Decimal
from typing import Any

from quant_data_hub.integrations.tushare import (
    TushareDailyBarsRequest,
    TushareMarketDataClient,
    resolve_price_factor,
)


class FakeDataFrame:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self.rows = rows
        self.empty = len(rows) == 0

    def to_dict(self, orient: str) -> list[dict[str, Any]]:
        if orient != "records":
            raise ValueError("fake dataframe only supports records")
        return self.rows


class FakeTushareProClient:
    def __init__(
        self,
        *,
        daily_rows: dict[str, list[dict[str, Any]]],
        adjustment_rows: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.daily_rows = daily_rows
        self.adjustment_rows = adjustment_rows or {}
        self.daily_calls: list[str] = []
        self.adjustment_calls: list[str] = []

    def daily(self, *, ts_code: str, start_date: str, end_date: str) -> FakeDataFrame:
        self.daily_calls.append(ts_code)
        return FakeDataFrame(self.daily_rows.get(ts_code, []))

    def adj_factor(self, *, ts_code: str, start_date: str, end_date: str) -> FakeDataFrame:
        self.adjustment_calls.append(ts_code)
        return FakeDataFrame(self.adjustment_rows.get(ts_code, []))


class TushareIntegrationTest(unittest.TestCase):
    def test_should_map_raw_daily_rows_to_market_bars_without_adjustment_call(self) -> None:
        pro_client = FakeTushareProClient(
            daily_rows={
                "000001.SZ": [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260601",
                        "open": "10",
                        "high": "11",
                        "low": "9",
                        "close": "10.5",
                        "pre_close": "10.1",
                        "change": "0.4",
                        "pct_chg": "3.96",
                        "vol": "1000",
                        "amount": "10500",
                    }
                ]
            }
        )
        client = TushareMarketDataClient(pro_client=pro_client)

        response = client.fetch_daily_bars(
            request=TushareDailyBarsRequest(
                symbols=["000001.SZ"],
                start_date="20260601",
                end_date="20260601",
                price_mode="raw",
            )
        )

        self.assertEqual(response.row_count, 1)
        self.assertEqual(response.bars[0].symbol, "000001.SZ")
        self.assertEqual(response.bars[0].trade_date.isoformat(), "2026-06-01")
        self.assertEqual(response.bars[0].close_price, Decimal("10.5"))
        self.assertIsNone(response.bars[0].adjustment_factor)
        self.assertEqual(pro_client.adjustment_calls, [])

    def test_should_apply_qfq_adjustment_factor_when_price_mode_is_qfq(self) -> None:
        pro_client = FakeTushareProClient(
            daily_rows={
                "000001.SZ": [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260601",
                        "open": "10",
                        "high": "12",
                        "low": "9",
                        "close": "10",
                        "pre_close": "9.8",
                        "change": "0.2",
                        "pct_chg": "2.04",
                        "vol": "1000",
                        "amount": "10000",
                    },
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260602",
                        "open": "12",
                        "high": "13",
                        "low": "11",
                        "close": "12",
                        "pre_close": "10",
                        "change": "2",
                        "pct_chg": "20",
                        "vol": "1100",
                        "amount": "13200",
                    },
                ]
            },
            adjustment_rows={
                "000001.SZ": [
                    {"trade_date": "20260601", "adj_factor": "2"},
                    {"trade_date": "20260602", "adj_factor": "4"},
                ]
            },
        )
        client = TushareMarketDataClient(pro_client=pro_client)

        response = client.fetch_daily_bars(
            request=TushareDailyBarsRequest(
                symbols=["000001.SZ"],
                start_date="20260601",
                end_date="20260602",
                price_mode="qfq",
            )
        )

        self.assertEqual(response.row_count, 2)
        self.assertEqual(response.bars[0].close_price, Decimal("5.0"))
        self.assertEqual(response.bars[0].adjustment_factor, Decimal("2"))
        self.assertEqual(response.bars[1].close_price, Decimal("12"))
        self.assertEqual(response.bars[1].adjustment_factor, Decimal("4"))

    def test_should_reject_qfq_when_adjustment_factor_is_missing(self) -> None:
        pro_client = FakeTushareProClient(
            daily_rows={
                "000001.SZ": [
                    {
                        "ts_code": "000001.SZ",
                        "trade_date": "20260601",
                        "open": "10",
                        "high": "11",
                        "low": "9",
                        "close": "10",
                    }
                ]
            },
            adjustment_rows={"000001.SZ": []},
        )
        client = TushareMarketDataClient(pro_client=pro_client)

        with self.assertRaises(ValueError):
            client.fetch_daily_bars(
                request=TushareDailyBarsRequest(
                    symbols=["000001.SZ"],
                    start_date="20260601",
                    end_date="20260601",
                    price_mode="qfq",
                )
            )

    def test_should_resolve_raw_price_factor_to_one(self) -> None:
        factor = resolve_price_factor(
            price_mode="raw",
            adjustment_factor=Decimal("2"),
            latest_adjustment_factor=Decimal("4"),
        )

        self.assertEqual(factor, Decimal("1"))


if __name__ == "__main__":
    unittest.main()
