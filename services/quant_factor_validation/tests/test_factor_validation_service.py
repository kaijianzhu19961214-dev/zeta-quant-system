import unittest

from quant_contracts import (
    FactorDailyValue,
    FactorValidationRequest,
    MarketBar,
    MarketBarsMeta,
    MarketBarsQuery,
    MarketBarsResponse,
)
from quant_factor_validation.services import FactorValidationService


class FakeMarketDataReader:
    def __init__(self) -> None:
        self.queries: list[MarketBarsQuery] = []

    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        self.queries.append(query)
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=query.timeframe,
                price_mode=query.price_mode,
                row_count=6,
                dataset_code="a_share_1d",
                batch_id=query.batch_id,
            ),
            rows=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-16", close_price="11"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000002.SZ", trade_date="2026-03-16", close_price="12"),
                MarketBar(symbol="000003.SZ", trade_date="2026-03-13", close_price="10"),
                MarketBar(symbol="000003.SZ", trade_date="2026-03-16", close_price="13"),
            ],
        )


class FactorValidationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_validate_factor_and_query_standard_market_fields(self) -> None:
        reader = FakeMarketDataReader()
        service = FactorValidationService(market_data_reader=reader)
        request = FactorValidationRequest(
            factor_name="momentum_1d",
            factor_values=[
                FactorDailyValue(
                    symbol="000001.SZ",
                    trade_date="2026-03-13",
                    factor_name="momentum_1d",
                    factor_value="0.1",
                ),
                FactorDailyValue(
                    symbol="000002.SZ",
                    trade_date="2026-03-13",
                    factor_name="momentum_1d",
                    factor_value="0.2",
                ),
                FactorDailyValue(
                    symbol="000003.SZ",
                    trade_date="2026-03-13",
                    factor_name="momentum_1d",
                    factor_value="0.3",
                ),
            ],
            market_start="2026-03-13",
            market_end="2026-03-16",
            forward_days=1,
            group_count=3,
            run_id="run_validation_test",
        )

        response = await service.validate(request=request)

        self.assertEqual(reader.queries[0].fields, ["symbol", "trade_date", "close_price"])
        self.assertEqual(response.metrics.effective_sample_count, 3)
        self.assertEqual(response.metrics.dataset_code, "a_share_1d")
        self.assertEqual(response.metrics.group_count, 3)
        self.assertAlmostEqual(response.metrics.group_return_spread_mean, 0.2)
        self.assertEqual(response.ic_series[0].rank_ic, 1.0)
        self.assertEqual(len(response.group_returns), 3)
        self.assertAlmostEqual(response.group_returns[2].average_forward_return, 0.3)
        self.assertEqual(response.report.decision, "review_required")
        self.assertEqual(response.manifest.persistence_status, "not_persisted")
        self.assertEqual(response.manifest.task_run.task_type, "factor_validation")
        self.assertEqual(
            response.manifest.artifacts[3].object_key,
            "factor_validation/momentum_1d/run_validation_test/group_returns.json",
        )
        self.assertEqual(
            response.manifest.artifacts[0].object_key,
            "factor_validation/momentum_1d/run_validation_test/validation_report.json",
        )
        self.assertIsNotNone(response.manifest.artifacts[0].file_size_bytes)
        self.assertEqual(
            response.manifest.artifacts[0].metadata["content_type"],
            "application/json",
        )
        self.assertIn("sha256", response.manifest.artifacts[0].metadata)


if __name__ == "__main__":
    unittest.main()
