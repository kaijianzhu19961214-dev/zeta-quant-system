from collections.abc import Sequence
import re

from quant_contracts import (
    AlgorithmCapability,
    AlgorithmParameterSpec,
    AlgorithmSpec,
    AssetClass,
    FactorCalculationRequest,
    FactorDailyValue,
    FactorFamily,
    FactorMode,
    MarketBar,
    Timeframe,
)

from quant_factor_lab.factors import calculate_momentum_factor

MOMENTUM_FACTOR_PATTERN = re.compile(r"^momentum_(?P<window>[1-9][0-9]*)d$")
MOMENTUM_ALGORITHM_ID = "technical.momentum"


class MomentumAlgorithmAdapter:
    def describe(self) -> AlgorithmSpec:
        return AlgorithmSpec(
            algorithm_id=MOMENTUM_ALGORITHM_ID,
            display_name="Momentum return factor",
            status="available",
            description="Calculates close-to-close momentum over the window encoded in factor_name.",
            adapter_module="quant_factor_lab.algorithms.technical.momentum_adapter",
            capability=AlgorithmCapability(
                asset_classes=[AssetClass.EQUITY, AssetClass.FUTURES],
                factor_modes=[FactorMode.CROSS_SECTIONAL, FactorMode.TIME_SERIES],
                factor_families=[FactorFamily.PRICE_VOLUME],
                timeframes=[Timeframe.DAY_1],
                output_kinds=["factor_values"],
            ),
            parameters=[
                AlgorithmParameterSpec(
                    name="lookback_window",
                    value_type="integer",
                    description="Return lookback window in trading days. Must match factor_name, e.g. momentum_20d.",
                    default_value=20,
                    minimum=1,
                    maximum=252,
                )
            ],
            tags=["price_volume", "momentum", "baseline"],
            research_notes=[
                "Baseline adapter used to verify the algorithm registry contract.",
                "Does not use future prices because each row only references earlier closes.",
            ],
        )

    def can_handle(self, *, request: FactorCalculationRequest) -> bool:
        if request.algorithm_id is not None and request.algorithm_id != MOMENTUM_ALGORITHM_ID:
            return False
        return MOMENTUM_FACTOR_PATTERN.fullmatch(request.factor_name) is not None

    def resolve_lookback_window(self, *, request: FactorCalculationRequest) -> int:
        match = MOMENTUM_FACTOR_PATTERN.fullmatch(request.factor_name)
        if match is None:
            raise ValueError("momentum adapter only supports momentum_*d factors")

        window = int(match.group("window"))
        if window > 252:
            raise ValueError("momentum window must be less than or equal to 252")
        if request.lookback_window != window:
            raise ValueError("lookback_window must match the window encoded in factor_name")
        return window

    def required_market_fields(self, *, request: FactorCalculationRequest) -> list[str]:
        return ["symbol", "trade_date", "close_price", "volume", "turnover"]

    def calculate(
        self,
        *,
        request: FactorCalculationRequest,
        bars: Sequence[MarketBar],
    ) -> list[FactorDailyValue]:
        return calculate_momentum_factor(
            bars=bars,
            factor_name=request.factor_name,
            lookback_window=self.resolve_lookback_window(request=request),
            asset_class=request.asset_class,
            factor_mode=request.factor_mode,
            factor_family=request.factor_family,
            universe_name=request.universe_name,
            data_source=request.data_source,
            data_version=request.data_version,
            factor_version=request.factor_version,
            run_id=request.run_id,
        )
