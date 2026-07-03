from datetime import date
import unittest

from quant_contracts import (
    MarketBar,
    MarketBarsMeta,
    MarketBarsQuery,
    MarketBarsResponse,
    PriceMode,
    Timeframe,
)

from quant_ops_api.schemas import MarketDataBarsSampleRequest, QfqBatchSummary
from quant_ops_api.schemas.market_data import (
    MarketDataIngestionLedgerPreview,
    MarketDataIngestionQualityCheckRecord,
    MarketDataIngestionRunRecord,
    MarketDataSourceCoverageItem,
)
from quant_ops_api.services.market_data_service import MarketDataService


class FakeQuantDataHubClient:
    def __init__(self) -> None:
        self.market_query: MarketBarsQuery | None = None

    async def list_qfq_batches(self, *, limit: int = 20) -> list[QfqBatchSummary]:
        return [
            QfqBatchSummary(
                batch_id="qfq_20260610",
                qfq_base_date=date(2026, 6, 10),
                status="succeeded",
            )
        ]

    async def query_market_bars(self, *, request: MarketBarsQuery) -> MarketBarsResponse:
        self.market_query = request
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                row_count=1,
                dataset_code="a_share_1d",
                batch_id=request.batch_id,
            ),
            rows=[
                MarketBar(
                    symbol=request.symbols[0],
                    trade_date=date(2026, 6, 10),
                    close_price="10.00",
                )
            ],
        )

    async def get_source_coverage(self, *, limit: int = 100) -> list[MarketDataSourceCoverageItem]:
        return [
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
        ]

    async def get_ingestion_ledger_preview(self, *, limit: int = 100) -> MarketDataIngestionLedgerPreview:
        return MarketDataIngestionLedgerPreview(
            generated_at="2026-07-02T16:00:00Z",
            persistence_status="not_persisted",
            run_count=1,
            quality_check_count=3,
            runs=[
                MarketDataIngestionRunRecord(
                    run_id="ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                    task_type="market_data_ingestion",
                    source_name="tushare_proxy",
                    dataset_code="a_share_1d",
                    timeframe="1d",
                    status="succeeded",
                    storage_target="clickhouse:market_data_1d_raw",
                    start_date=date(2024, 1, 2),
                    end_date=date(2026, 6, 30),
                    row_count=3244082,
                    symbol_count=5620,
                    trading_day_count=601,
                    duplicate_key_rows=0,
                )
            ],
            quality_checks=[
                MarketDataIngestionQualityCheckRecord(
                    check_id="check_row_count_positive",
                    run_id="ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                    check_name="row_count_positive",
                    check_status="passed",
                    expected_condition="row_count > 0",
                    observed_value="3244082",
                ),
                MarketDataIngestionQualityCheckRecord(
                    check_id="check_duplicate_key_rows_zero",
                    run_id="ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                    check_name="duplicate_key_rows_zero",
                    check_status="passed",
                    expected_condition="duplicate_key_rows = 0",
                    observed_value="0",
                ),
                MarketDataIngestionQualityCheckRecord(
                    check_id="check_date_range_present",
                    run_id="ingestion_tushare_proxy_a_share_1d_1d_2024_01_02_2026_06_30",
                    check_name="date_range_present",
                    check_status="passed",
                    expected_condition="min_date and max_date are present",
                    observed_value="2024-01-02..2026-06-30",
                ),
            ],
            limitations=["preview only"],
        )


class MarketDataServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_resolve_latest_qfq_batch_for_sample_query(self) -> None:
        client = FakeQuantDataHubClient()
        service = MarketDataService(quant_data_hub_client=client)
        request = MarketDataBarsSampleRequest(
            symbol="000001.SZ",
            timeframe="1d",
            start="2026-06-10",
            end="2026-06-10",
            price_mode="qfq",
            limit=5,
        )

        response = await service.query_sample_bars(request=request)

        self.assertIsNotNone(client.market_query)
        self.assertEqual(client.market_query.price_mode, PriceMode.QFQ)
        self.assertEqual(client.market_query.timeframe, Timeframe.DAY_1)
        self.assertEqual(client.market_query.batch_id, "qfq_20260610")
        self.assertEqual(response.request.batch_id, "qfq_20260610")
        self.assertEqual(response.meta.batch_id, "qfq_20260610")
        self.assertEqual(response.meta.qfq_base_date, date(2026, 6, 10))

    async def test_should_return_source_coverage_with_storage_roles(self) -> None:
        client = FakeQuantDataHubClient()
        service = MarketDataService(quant_data_hub_client=client)

        response = await service.get_source_coverage()

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.row_count, 1)
        self.assertEqual(response.coverage[0].source_name, "tushare_proxy")
        self.assertEqual(response.coverage[0].row_count, 3244082)
        self.assertEqual([role.storage_name for role in response.storage_roles], ["postgresql", "clickhouse", "minio", "redis"])
        self.assertTrue(next(role for role in response.storage_roles if role.storage_name == "clickhouse").stores_market_bars)

    async def test_should_return_ingestion_ledger_preview_with_storage_roles(self) -> None:
        client = FakeQuantDataHubClient()
        service = MarketDataService(quant_data_hub_client=client)

        response = await service.get_ingestion_ledger_preview()

        self.assertEqual(response.status, "ok")
        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.run_count, 1)
        self.assertEqual(response.quality_check_count, 3)
        self.assertEqual(response.runs[0].source_name, "tushare_proxy")
        self.assertEqual(response.quality_checks[0].check_status, "passed")
        self.assertEqual([role.storage_name for role in response.storage_roles], ["postgresql", "clickhouse", "minio", "redis"])


if __name__ == "__main__":
    unittest.main()
