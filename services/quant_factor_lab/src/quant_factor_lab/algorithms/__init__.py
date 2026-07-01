from quant_factor_lab.algorithms.registry import FactorAlgorithmRegistry
from quant_factor_lab.algorithms.technical import MomentumAlgorithmAdapter
from quant_factor_lab.algorithms.volatility import build_planned_garch_algorithm_specs


def create_default_algorithm_registry() -> FactorAlgorithmRegistry:
    registry = FactorAlgorithmRegistry()
    registry.register_adapter(adapter=MomentumAlgorithmAdapter())
    for spec in build_planned_garch_algorithm_specs():
        registry.register_planned_spec(spec=spec)
    return registry


__all__ = [
    "FactorAlgorithmRegistry",
    "MomentumAlgorithmAdapter",
    "build_planned_garch_algorithm_specs",
    "create_default_algorithm_registry",
]
