from quant_contracts import AlgorithmSpec, FactorCalculationRequest

from quant_factor_lab.algorithms.base import FactorAlgorithmAdapter


class FactorAlgorithmRegistry:
    def __init__(self) -> None:
        self._adapters: list[FactorAlgorithmAdapter] = []
        self._planned_specs: dict[str, AlgorithmSpec] = {}

    def register_adapter(self, *, adapter: FactorAlgorithmAdapter) -> None:
        self._adapters.append(adapter)

    def register_planned_spec(self, *, spec: AlgorithmSpec) -> None:
        if spec.status != "planned":
            raise ValueError("planned spec registry only accepts planned algorithms")
        self._planned_specs[spec.algorithm_id] = spec

    def list_specs(self, *, include_planned: bool = True) -> list[AlgorithmSpec]:
        specs = [adapter.describe() for adapter in self._adapters]
        if include_planned:
            specs.extend(self._planned_specs.values())
        return sorted(specs, key=lambda spec: spec.algorithm_id)

    def resolve_factor_adapter(self, *, request: FactorCalculationRequest) -> FactorAlgorithmAdapter:
        for adapter in self._adapters:
            if adapter.can_handle(request=request):
                return adapter

        if request.algorithm_id and request.algorithm_id in self._planned_specs:
            raise ValueError(f"algorithm is registered but not implemented yet: {request.algorithm_id}")
        raise ValueError(f"no factor algorithm adapter supports factor_name={request.factor_name}")
