import unittest
from datetime import date

from quant_contracts import Timeframe
from quant_data_hub.schemas.source_coverage import (
    MarketDataSourceCoverageItem,
    MarketDataSourceCoverageResponse,
)
from quant_data_hub.services.ingestion_ledger_service import IngestionLedgerService


class FakeMarketQueryService:
    async def list_source_coverage(self, *, limit: int = 100) -> MarketDataSourceCoverageResponse:
        return MarketDataSourceCoverageResponse(
            row_count=1,
            coverage=[
                MarketDataSourceCoverageItem(
                    timeframe=Timeframe.DAY_1,
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
        )


class IngestionLedgerServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_build_preview_ledger_from_source_coverage(self) -> None:
        service = IngestionLedgerService(market_query_service=FakeMarketQueryService())

        response = await service.preview_ledger(limit=10)

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.run_count, 1)
        self.assertEqual(response.quality_check_count, 3)
        self.assertEqual(response.runs[0].status, "succeeded")
        self.assertEqual(response.runs[0].storage_target, "clickhouse:market_data_1d_raw")
        self.assertEqual(response.runs[0].row_count, 3244082)
        self.assertEqual(
            [check.check_status for check in response.quality_checks],
            ["passed", "passed", "passed"],
        )


if __name__ == "__main__":
    unittest.main()
