from datetime import date, datetime, timezone
import unittest

from fastapi.testclient import TestClient
from quant_contracts import MarketBar, MarketBarsMeta, PriceMode, Timeframe

from quant_ops_api.api.v1.dependencies import get_market_data_service
from quant_ops_api.main import create_app
from quant_ops_api.schemas import (
    MarketDataBarsSampleRequest,
    MarketDataBarsSampleResponse,
    MarketDataPriceModeOverview,
    MarketDataSourceCoverageItem,
    MarketDataSourceCoverageResponse,
    MarketDataStorageRole,
    MarketPriceModeStatus,
    QfqBatchSummary,
)


class FakeMarketDataService:
    async def get_price_mode_overview(self) -> MarketDataPriceModeOverview:
        latest_batch = QfqBatchSummary(
            batch_id="qfq_20260313",
            qfq_base_date=date(2026, 3, 13),
            status="succeeded",
        )
        return MarketDataPriceModeOverview(
            status="ok",
            generated_at=datetime.now(timezone.utc),
            qfq_batch_count=1,
            latest_qfq_batch=latest_batch,
            price_modes=[
                MarketPriceModeStatus(
                    price_mode="raw",
                    display_name="原始价格 / Raw",
                    storage_object="market_data_*_raw",
                    source_relation="Direct ClickHouse raw table query.",
                    requires_batch_id=False,
                    available=True,
                ),
                MarketPriceModeStatus(
                    price_mode="qfq",
                    display_name="前复权 / QFQ",
                    storage_object="market_data_*_qfq_cache",
                    source_relation="QFQ cache joined with raw table for non-price fields.",
                    requires_batch_id=True,
                    available=True,
                    latest_batch_id=latest_batch.batch_id,
                    latest_qfq_base_date=latest_batch.qfq_base_date,
                ),
                MarketPriceModeStatus(
                    price_mode="hfq",
                    display_name="后复权 / HFQ",
                    storage_object="v_market_data_*_hfq",
                    source_relation="ClickHouse view calculates raw price multiplied by hfq_factor.",
                    requires_batch_id=False,
                    available=True,
                ),
            ],
            limitations=[],
        )

    async def query_sample_bars(self, *, request: MarketDataBarsSampleRequest) -> MarketDataBarsSampleResponse:
        self.last_sample_request = request
        return MarketDataBarsSampleResponse(
            generated_at=datetime.now(timezone.utc),
            request=request,
            meta=MarketBarsMeta(
                timeframe=Timeframe.DAY_1,
                price_mode=PriceMode.RAW,
                row_count=1,
                dataset_code="a_share_1d",
            ),
            rows=[
                MarketBar(
                    symbol=request.symbol,
                    trade_date=date(2026, 6, 10),
                    close_price="11.32",
                    adjustment_factor="134.5794",
                )
            ],
            limitations=[],
        )

    async def get_source_coverage(self, *, limit: int = 100) -> MarketDataSourceCoverageResponse:
        return MarketDataSourceCoverageResponse(
            status="ok",
            generated_at=datetime.now(timezone.utc),
            row_count=1,
            coverage=[
                MarketDataSourceCoverageItem(
                    timeframe="1d",
                    storage_object="market_data_1d_raw",
                    dataset_code="a_share_1d",
                    source_name="tushare_proxy",
                    row_count=3244082,
                    symbol_count=5620,
                    trading_day_count=601,
                    min_date=date(2024, 1, 2),
                    max_date=date(2026, 6, 30),
                    duplicate_key_rows=0,
                )
            ],
            storage_roles=[
                MarketDataStorageRole(
                    storage_name="clickhouse",
                    display_name="ClickHouse",
                    responsibility="market bars",
                    current_usage="stores a_share_1d",
                    stores_market_bars=True,
                )
            ],
            limitations=[],
        )


class MarketDataRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_market_data_service] = lambda: FakeMarketDataService()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_return_market_data_price_mode_overview(self) -> None:
        response = self.client.get("/api/v1/market-data/price-modes")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["qfq_batch_count"], 1)
        self.assertEqual(payload["latest_qfq_batch"]["batch_id"], "qfq_20260313")
        self.assertEqual([item["price_mode"] for item in payload["price_modes"]], ["raw", "qfq", "hfq"])

    def test_should_return_market_data_bars_sample(self) -> None:
        response = self.client.post(
            "/api/v1/market-data/bars/sample",
            json={
                "symbol": "000001.sz",
                "timeframe": "1d",
                "start": "2026-06-10",
                "end": "2026-06-10",
                "price_mode": "raw",
                "limit": 5,
            },
        )
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["request"]["symbol"], "000001.SZ")
        self.assertEqual(payload["meta"]["row_count"], 1)
        self.assertEqual(payload["rows"][0]["close_price"], "11.32")

    def test_should_return_market_data_source_coverage(self) -> None:
        response = self.client.get("/api/v1/market-data/source-coverage")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["coverage"][0]["source_name"], "tushare_proxy")
        self.assertEqual(payload["coverage"][0]["row_count"], 3244082)
        self.assertEqual(payload["storage_roles"][0]["storage_name"], "clickhouse")


if __name__ == "__main__":
    unittest.main()
