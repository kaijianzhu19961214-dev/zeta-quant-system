import unittest

from quant_contracts import FactorCalculationRequest

from quant_factor_lab.algorithms import create_default_algorithm_registry


class AlgorithmRegistryTest(unittest.TestCase):
    def test_should_list_available_and_planned_algorithm_specs(self) -> None:
        registry = create_default_algorithm_registry()

        specs = registry.list_specs(include_planned=True)
        algorithm_ids = [spec.algorithm_id for spec in specs]

        self.assertIn("technical.momentum", algorithm_ids)
        self.assertIn("volatility.egarch", algorithm_ids)
        self.assertIn("volatility.gjr_garch", algorithm_ids)
        self.assertIn("volatility.aparch", algorithm_ids)

    def test_should_mark_available_algorithms_without_missing_required_gates(self) -> None:
        registry = create_default_algorithm_registry()

        available_specs = [
            spec
            for spec in registry.list_specs(include_planned=True)
            if spec.status == "available"
        ]

        self.assertGreaterEqual(len(available_specs), 1)
        for spec in available_specs:
            missing_required_gates = [
                gate
                for gate in spec.review_gates
                if gate.is_required and gate.status == "missing"
            ]
            self.assertEqual(missing_required_gates, [])

    def test_should_expose_validation_evidence_gate_for_momentum(self) -> None:
        registry = create_default_algorithm_registry()

        momentum_spec = next(
            spec
            for spec in registry.list_specs(include_planned=True)
            if spec.algorithm_id == "technical.momentum"
        )
        gate_ids = [gate.gate_id for gate in momentum_spec.review_gates]

        self.assertIn("validation_evidence", gate_ids)

    def test_should_expose_missing_review_gates_for_planned_garch_algorithms(self) -> None:
        registry = create_default_algorithm_registry()

        egarch_spec = next(
            spec
            for spec in registry.list_specs(include_planned=True)
            if spec.algorithm_id == "volatility.egarch"
        )
        missing_gate_ids = [
            gate.gate_id
            for gate in egarch_spec.review_gates
            if gate.status == "missing"
        ]

        self.assertEqual(egarch_spec.status, "planned")
        self.assertIn("data_policy_fixed", missing_gate_ids)
        self.assertIn("validation_evidence", missing_gate_ids)

    def test_should_resolve_momentum_adapter_from_factor_name(self) -> None:
        registry = create_default_algorithm_registry()
        request = FactorCalculationRequest(
            factor_name="momentum_2d",
            symbols=["000001.SZ"],
            start="2026-03-11",
            end="2026-03-13",
            lookback_window=2,
        )

        adapter = registry.resolve_factor_adapter(request=request)

        self.assertEqual(adapter.describe().algorithm_id, "technical.momentum")

    def test_should_report_planned_algorithm_as_not_implemented(self) -> None:
        registry = create_default_algorithm_registry()
        request = FactorCalculationRequest(
            factor_name="egarch_volatility_20d",
            algorithm_id="volatility.egarch",
            symbols=["000001.SZ"],
            start="2026-03-11",
            end="2026-03-13",
            lookback_window=20,
        )

        with self.assertRaisesRegex(ValueError, "not implemented"):
            registry.resolve_factor_adapter(request=request)


if __name__ == "__main__":
    unittest.main()
