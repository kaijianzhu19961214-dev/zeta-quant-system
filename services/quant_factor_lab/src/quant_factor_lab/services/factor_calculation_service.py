from quant_contracts import (
    AlgorithmSpec,
    FactorCalculationMeta,
    FactorCalculationRequest,
    FactorCalculationResponse,
    MarketBarsQuery,
)

from quant_factor_lab.algorithms import FactorAlgorithmRegistry, create_default_algorithm_registry
from quant_factor_lab.repositories.market_data_reader import MarketDataReader


class FactorCalculationService:
    def __init__(
        self,
        *,
        market_data_reader: MarketDataReader,
        algorithm_registry: FactorAlgorithmRegistry | None = None,
    ) -> None:
        self.market_data_reader = market_data_reader
        self.algorithm_registry = algorithm_registry or create_default_algorithm_registry()

    def list_algorithms(self) -> list[AlgorithmSpec]:
        return self.algorithm_registry.list_specs(include_planned=True)

    async def calculate(self, *, request: FactorCalculationRequest) -> FactorCalculationResponse:
        adapter = self.algorithm_registry.resolve_factor_adapter(request=request)
        algorithm_spec = adapter.describe()
        lookback_window = adapter.resolve_lookback_window(request=request)

        market_response = await self.market_data_reader.query_bars(
            query=MarketBarsQuery(
                timeframe=request.timeframe,
                symbols=request.symbols,
                start=request.start,
                end=request.end,
                price_mode=request.price_mode,
                dataset_code=request.dataset_code,
                batch_id=request.batch_id,
                fields=adapter.required_market_fields(request=request),
                limit=request.limit,
            )
        )

        values = adapter.calculate(request=request, bars=market_response.rows)

        return FactorCalculationResponse(
            meta=FactorCalculationMeta(
                factor_name=request.factor_name,
                algorithm_id=algorithm_spec.algorithm_id,
                algorithm_version=algorithm_spec.version,
                algorithm_source_library=algorithm_spec.source_library,
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                row_count=len(values),
                lookback_window=lookback_window,
                universe_name=request.universe_name,
                data_source=request.data_source,
                data_version=request.data_version,
                factor_version=request.factor_version,
                run_id=request.run_id,
                dataset_code=request.dataset_code or market_response.meta.dataset_code,
                batch_id=request.batch_id or market_response.meta.batch_id,
            ),
            rows=values,
        )
