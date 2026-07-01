from collections.abc import Sequence
from typing import Protocol

from quant_contracts import AlgorithmSpec, FactorCalculationRequest, FactorDailyValue, MarketBar


class FactorAlgorithmAdapter(Protocol):
    def describe(self) -> AlgorithmSpec:
        """Return static metadata for registry and review."""

    def can_handle(self, *, request: FactorCalculationRequest) -> bool:
        """Return whether this adapter supports the requested factor calculation."""

    def resolve_lookback_window(self, *, request: FactorCalculationRequest) -> int:
        """Resolve the effective lookback window from request and algorithm rules."""

    def required_market_fields(self, *, request: FactorCalculationRequest) -> list[str]:
        """Return market fields required before calculation."""

    def calculate(
        self,
        *,
        request: FactorCalculationRequest,
        bars: Sequence[MarketBar],
    ) -> list[FactorDailyValue]:
        """Calculate factor values from standardized market bars."""
