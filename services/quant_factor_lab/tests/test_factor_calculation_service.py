import unittest

from quant_contracts import FactorCalculationRequest, MarketBar, MarketBarsMeta, MarketBarsQuery, MarketBarsResponse
from quant_factor_lab.services.factor_calculation_service import FactorCalculationService


class FakeMarketDataReader:
    def __init__(self) -> None:
        self.queries: list[MarketBarsQuery] = []

    async def query_bars(self, *, query: MarketBarsQuery) -> MarketBarsResponse:
        self.queries.append(query)
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=query.timeframe,
                price_mode=query.price_mode,
                row_count=3,
                dataset_code="a_share_1d",
                batch_id=query.batch_id,
            ),
            rows=[
                MarketBar(symbol="000001.SZ", trade_date="2026-03-11", close_price="10"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-12", close_price="11"),
                MarketBar(symbol="000001.SZ", trade_date="2026-03-13", close_price="15"),
            ],
        )


class FactorCalculationServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_calculate_momentum_and_query_standard_market_fields(self) -> None:
        reader = FakeMarketDataReader()
        service = FactorCalculationService(market_data_reader=reader)
        request = FactorCalculationRequest(
            factor_name="momentum_2d",
            symbols=["000001.SZ"],
            start="2026-03-11",
            end="2026-03-13",
            lookback_window=2,
            run_id="run_service_test",
        )

        response = await service.calculate(request=request)

        self.assertEqual(reader.queries[0].fields, ["symbol", "trade_date", "close_price", "volume", "turnover"])
        self.assertEqual(response.meta.dataset_code, "a_share_1d")
        self.assertEqual(str(response.rows[2].factor_value), "0.5")

    async def test_should_reject_request_when_factor_window_does_not_match_name(self) -> None:
        service = FactorCalculationService(market_data_reader=FakeMarketDataReader())
        request = FactorCalculationRequest(
            factor_name="momentum_2d",
            symbols=["000001.SZ"],
            start="2026-03-11",
            end="2026-03-13",
            lookback_window=3,
        )

        with self.assertRaises(ValueError):
            await service.calculate(request=request)


if __name__ == "__main__":
    unittest.main()
