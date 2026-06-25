from quant_contracts import (
    FactorDailyValue,
    FactorValidationMetric,
    FactorValidationRequest,
    FactorValidationResponse,
    MarketBarsQuery,
)

from quant_factor_validation.metrics import (
    calculate_forward_returns,
    calculate_ic_series,
    mean_optional,
    standard_deviation,
)
from quant_factor_validation.repositories.market_data_reader import MarketDataReader
from quant_factor_validation.services.validation_manifest import build_validation_manifest
from quant_factor_validation.services.validation_report import build_validation_report


class FactorValidationService:
    def __init__(self, *, market_data_reader: MarketDataReader) -> None:
        self.market_data_reader = market_data_reader

    async def validate(self, *, request: FactorValidationRequest) -> FactorValidationResponse:
        symbols = sorted({factor_value.symbol for factor_value in request.factor_values})
        market_response = await self.market_data_reader.query_bars(
            query=MarketBarsQuery(
                timeframe=request.timeframe,
                symbols=symbols,
                start=request.market_start,
                end=request.market_end,
                price_mode=request.price_mode,
                dataset_code=request.dataset_code,
                batch_id=request.batch_id,
                fields=["symbol", "trade_date", "close_price"],
                limit=request.limit,
            )
        )

        forward_returns = calculate_forward_returns(
            bars=market_response.rows,
            forward_days=request.forward_days,
        )
        ic_series = calculate_ic_series(
            factor_values=request.factor_values,
            forward_returns=forward_returns,
        )
        ic_values = [point.ic for point in ic_series]
        rank_ic_values = [point.rank_ic for point in ic_series]
        ic_std = standard_deviation(ic_values)
        ic_mean = mean_optional(ic_values)
        effective_sample_count = sum(point.sample_size for point in ic_series)

        metrics = FactorValidationMetric(
            factor_name=request.factor_name,
            start_date=min(value.trade_date for value in request.factor_values),
            end_date=max(value.trade_date for value in request.factor_values),
            forward_days=request.forward_days,
            sample_count=len(request.factor_values),
            effective_sample_count=effective_sample_count,
            coverage_ratio=_calculate_coverage_ratio(
                effective_sample_count=effective_sample_count,
                sample_count=len(request.factor_values),
            ),
            missing_ratio=_calculate_missing_ratio(factor_values=request.factor_values),
            ic_mean=ic_mean,
            rank_ic_mean=mean_optional(rank_ic_values),
            ic_std=ic_std,
            ic_ir=_calculate_ic_ir(ic_mean=ic_mean, ic_std=ic_std),
            universe_name=request.universe_name,
            price_mode=request.price_mode,
            dataset_code=request.dataset_code or market_response.meta.dataset_code,
            batch_id=request.batch_id or market_response.meta.batch_id,
            validation_version=request.validation_version,
            run_id=request.run_id,
        )

        report = build_validation_report(metrics=metrics)

        return FactorValidationResponse(
            metrics=metrics,
            ic_series=ic_series,
            report=report,
            manifest=build_validation_manifest(
                request=request,
                metrics=metrics,
                report=report,
                ic_series=ic_series,
            ),
        )


def _calculate_coverage_ratio(*, effective_sample_count: int, sample_count: int) -> float | None:
    if sample_count == 0:
        return None
    return effective_sample_count / sample_count


def _calculate_missing_ratio(*, factor_values: list[FactorDailyValue]) -> float | None:
    if not factor_values:
        return None
    missing_count = sum(1 for value in factor_values if value.factor_value is None)
    return missing_count / len(factor_values)


def _calculate_ic_ir(*, ic_mean: float | None, ic_std: float | None) -> float | None:
    if ic_mean is None:
        return None
    if ic_std is None or ic_std == 0:
        return None
    return ic_mean / ic_std
