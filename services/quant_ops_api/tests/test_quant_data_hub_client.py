import unittest

import httpx
from quant_contracts import MarketBarsQuery, PriceMode, Timeframe

from quant_ops_api.clients import QuantDataHubClient, QuantDataHubClientError


class QuantDataHubClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_parse_qfq_batches(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-data-hub/api/v1/adjustments/qfq-batches?limit=2",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "row_count": 1,
                    "batches": [
                        {
                            "batch_id": "qfq_20260313",
                            "qfq_base_date": "2026-03-13",
                            "status": "succeeded",
                            "description": "Qfq cache build succeeded",
                        }
                    ],
                },
            )

        client = QuantDataHubClient(
            base_url="http://quant-data-hub",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        batches = await client.list_qfq_batches(limit=2)

        self.assertEqual(batches[0].batch_id, "qfq_20260313")
        self.assertEqual(batches[0].qfq_base_date.isoformat(), "2026-03-13")

    async def test_should_raise_client_error_when_batches_are_missing(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(status_code=200, json={"row_count": 0})

        client = QuantDataHubClient(
            base_url="http://quant-data-hub",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        with self.assertRaises(QuantDataHubClientError) as context:
            await client.list_qfq_batches()

        self.assertEqual(context.exception.status_code, 502)

    async def test_should_query_market_bars(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "http://quant-data-hub/api/v1/market-bars/query")
            self.assertEqual(request.method, "POST")
            self.assertEqual(request.read().decode(), (
                '{"timeframe":"1d","symbols":["000001.SZ"],"start":"2026-06-10",'
                '"end":"2026-06-10","price_mode":"raw","dataset_code":null,'
                '"batch_id":null,"fields":null,"limit":5}'
            ))
            return httpx.Response(
                status_code=200,
                json={
                    "meta": {
                        "timeframe": "1d",
                        "price_mode": "raw",
                        "row_count": 1,
                        "dataset_code": "a_share_1d",
                        "batch_id": None,
                    },
                    "rows": [
                        {
                            "symbol": "000001.SZ",
                            "trade_date": "2026-06-10",
                            "close_price": "11.32",
                        }
                    ],
                },
            )

        client = QuantDataHubClient(
            base_url="http://quant-data-hub",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )
        request = MarketBarsQuery(
            timeframe=Timeframe.DAY_1,
            symbols=["000001.SZ"],
            start="2026-06-10",
            end="2026-06-10",
            price_mode=PriceMode.RAW,
            limit=5,
        )

        response = await client.query_market_bars(request=request)

        self.assertEqual(response.meta.row_count, 1)
        self.assertEqual(str(response.rows[0].close_price), "11.32")

    async def test_should_parse_source_coverage(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-data-hub/api/v1/market-data/source-coverage?limit=5",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "generated_at": "2026-07-02T16:00:00Z",
                    "row_count": 1,
                    "coverage": [
                        {
                            "timeframe": "1d",
                            "storage_object": "market_data_1d_raw",
                            "dataset_code": "a_share_1d",
                            "source_name": "tushare_proxy",
                            "row_count": 3244082,
                            "symbol_count": 5620,
                            "trading_day_count": 601,
                            "min_date": "2024-01-02",
                            "max_date": "2026-06-30",
                            "duplicate_key_rows": 0,
                        }
                    ],
                },
            )

        client = QuantDataHubClient(
            base_url="http://quant-data-hub",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        coverage = await client.get_source_coverage(limit=5)

        self.assertEqual(coverage[0].source_name, "tushare_proxy")
        self.assertEqual(coverage[0].row_count, 3244082)
        self.assertEqual(coverage[0].min_date.isoformat(), "2024-01-02")

    async def test_should_parse_ingestion_ledger_preview(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(
                str(request.url),
                "http://quant-data-hub/api/v1/ingestion/ledger/preview?limit=5",
            )
            return httpx.Response(
                status_code=200,
                json={
                    "generated_at": "2026-07-02T16:00:00Z",
                    "persistence_status": "not_persisted",
                    "run_count": 1,
                    "quality_check_count": 1,
                    "runs": [
                        {
                            "run_id": "ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                            "task_type": "market_data_ingestion",
                            "source_name": "tushare_proxy",
                            "dataset_code": "a_share_1d",
                            "timeframe": "1d",
                            "status": "succeeded",
                            "storage_target": "clickhouse:market_data_1d_raw",
                            "start_date": "2024-01-02",
                            "end_date": "2026-06-30",
                            "row_count": 3244082,
                            "symbol_count": 5620,
                            "trading_day_count": 601,
                            "duplicate_key_rows": 0,
                            "output_summary": {},
                            "finished_at": "2026-07-02T16:00:00Z",
                        }
                    ],
                    "quality_checks": [
                        {
                            "check_id": "check_row_count_positive",
                            "run_id": "ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                            "check_name": "row_count_positive",
                            "check_status": "passed",
                            "expected_condition": "row_count > 0",
                            "observed_value": "3244082",
                        }
                    ],
                    "limitations": ["preview only"],
                },
            )

        client = QuantDataHubClient(
            base_url="http://quant-data-hub",
            timeout_seconds=5,
            transport=httpx.MockTransport(handler),
        )

        preview = await client.get_ingestion_ledger_preview(limit=5)

        self.assertEqual(preview.persistence_status, "not_persisted")
        self.assertEqual(preview.runs[0].source_name, "tushare_proxy")
        self.assertEqual(preview.quality_checks[0].check_status, "passed")


if __name__ == "__main__":
    unittest.main()
