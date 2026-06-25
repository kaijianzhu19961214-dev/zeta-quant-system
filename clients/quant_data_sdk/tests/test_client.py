import json
import unittest
from collections.abc import Callable
from typing import Any

import httpx
from quant_contracts import PriceMode, Timeframe

from quant_data_sdk import AsyncQuantDataClient, QuantDataApiError, QuantDataClient


class QuantDataClientTest(unittest.TestCase):
    def test_should_parse_health_when_service_returns_ok(self) -> None:
        client = self._build_client(
            lambda request: httpx.Response(
                status_code=200,
                json={"status": "ok", "service": "quant-data-hub"},
            )
        )

        response = client.health()

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.service, "quant-data-hub")
        client.close()

    def test_should_query_market_bars_when_payload_is_valid(self) -> None:
        captured_body: dict[str, Any] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_body.update(json.loads(request.content.decode("utf-8")))
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
                            "trade_date": "2026-03-13",
                            "close_price": "10.50",
                            "volume": "1000",
                        }
                    ],
                },
            )

        client = self._build_client(handler)

        response = client.market.get_bars(
            symbols=["000001.sz"],
            timeframe=Timeframe.DAY_1,
            start="2026-03-13",
            end="2026-03-13",
            fields=["symbol", "close_price"],
        )

        self.assertEqual(captured_body["symbols"], ["000001.SZ"])
        self.assertEqual(captured_body["timeframe"], "1d")
        self.assertEqual(response.meta.dataset_code, "a_share_1d")
        self.assertEqual(response.rows[0].symbol, "000001.SZ")
        self.assertEqual(str(response.rows[0].close_price), "10.50")
        client.close()

    def test_should_parse_qfq_batches_when_response_is_valid(self) -> None:
        client = self._build_client(
            lambda request: httpx.Response(
                status_code=200,
                json={
                    "row_count": 1,
                    "batches": [
                        {
                            "batch_id": "qfq_20260313",
                            "qfq_base_date": "2026-03-13",
                            "status": "success",
                            "description": "daily qfq batch",
                            "created_at": "2026-03-13T10:00:00",
                            "finished_at": "2026-03-13T10:05:00",
                        }
                    ],
                },
            )
        )

        response = client.adjustments.list_qfq_batches(limit=10)

        self.assertEqual(response.row_count, 1)
        self.assertEqual(response.batches[0].batch_id, "qfq_20260313")
        client.close()

    def test_should_raise_api_error_when_service_returns_error(self) -> None:
        client = self._build_client(
            lambda request: httpx.Response(
                status_code=502,
                json={"detail": "ClickHouse query failed"},
            )
        )

        with self.assertRaises(QuantDataApiError) as context:
            client.market.get_bars(
                symbols=["000001.SZ"],
                timeframe="1d",
                start="2026-03-13",
                end="2026-03-13",
                price_mode=PriceMode.RAW,
            )

        self.assertEqual(context.exception.status_code, 502)
        self.assertEqual(context.exception.message, "ClickHouse query failed")
        client.close()

    def test_should_reject_string_symbols_before_request(self) -> None:
        client = self._build_client(lambda request: httpx.Response(status_code=200, json={}))

        with self.assertRaises(ValueError):
            client.market.get_bars(
                symbols="000001.SZ",
                timeframe="1d",
                start="2026-03-13",
                end="2026-03-13",
            )

        client.close()

    def _build_client(self, handler: Callable[[httpx.Request], httpx.Response]) -> QuantDataClient:
        return QuantDataClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(handler),
        )


class AsyncQuantDataClientTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_query_market_bars_when_async_payload_is_valid(self) -> None:
        async def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                status_code=200,
                json={
                    "meta": {
                        "timeframe": "1d",
                        "price_mode": "raw",
                        "row_count": 0,
                        "dataset_code": "a_share_1d",
                        "batch_id": None,
                    },
                    "rows": [],
                },
            )

        client = AsyncQuantDataClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(handler),
        )

        response = await client.market.get_bars(
            symbols=["000001.SZ"],
            timeframe=Timeframe.DAY_1,
            start="2026-03-13",
            end="2026-03-13",
        )

        self.assertEqual(response.meta.row_count, 0)
        self.assertEqual(response.rows, [])
        await client.close()


if __name__ == "__main__":
    unittest.main()
