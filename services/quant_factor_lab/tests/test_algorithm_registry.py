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
