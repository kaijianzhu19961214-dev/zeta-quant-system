import unittest

from quant_contracts import (
    EvaluationEngine,
    ExternalFactorValidationSummary,
)
from quant_factor_validation.services.external_evaluation_adapter import (
    build_external_factor_evaluation_result,
    build_external_factor_validation_metric,
)
from quant_factor_validation.services.factor_scoring import build_factor_comparison_report


class ExternalEvaluationAdapterTest(unittest.TestCase):
    def test_should_map_alphalens_summary_to_standard_evaluation_result(self) -> None:
        summary = ExternalFactorValidationSummary(
            factor_name="momentum_20d",
            evaluation_engine=EvaluationEngine.ALPHALENS,
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=180,
            effective_sample_count=165,
            coverage_ratio=0.92,
            missing_ratio=0.04,
            ic_mean=0.035,
            rank_ic_mean=0.06,
            ic_std=0.08,
            ic_ir=0.4375,
            group_return_spread_mean=0.045,
            source_library="alphalens",
            source_version="0.4.0",
            source_metric_names=["mean_information_coefficient", "mean_quantile_returns_spread"],
        )

        result = build_external_factor_evaluation_result(summary=summary)

        self.assertEqual(result.factor_name, "momentum_20d")
        self.assertEqual(result.evaluation_engine, EvaluationEngine.ALPHALENS)
        self.assertEqual(result.metrics.evaluation_engine, EvaluationEngine.ALPHALENS)
        self.assertIsNotNone(result.report)
        self.assertIsNotNone(result.score_card)
        self.assertEqual(result.report.decision, "candidate_pass")
        self.assertGreater(result.score_card.final_score, 0)
        self.assertTrue(
            any(finding.code == "external_engine_adapter" for finding in result.report.findings)
        )

    def test_should_preserve_qlib_context_when_building_metric(self) -> None:
        summary = ExternalFactorValidationSummary(
            factor_name="alpha158_momentum",
            evaluation_engine=EvaluationEngine.QLIB,
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=1,
            sample_count=100,
            effective_sample_count=80,
            coverage_ratio=0.8,
            missing_ratio=0.1,
            rank_ic_mean=0.03,
            source_library="qlib",
            source_run_id="qlib_run_001",
            dataset_code="qlib_alpha158_sample",
        )

        metrics = build_external_factor_validation_metric(summary=summary)

        self.assertEqual(metrics.evaluation_engine, EvaluationEngine.QLIB)
        self.assertEqual(metrics.run_id, "qlib_run_001")
        self.assertEqual(metrics.dataset_code, "qlib_alpha158_sample")

    def test_should_build_cross_engine_comparison_from_external_results(self) -> None:
        alphalens_result = build_external_factor_evaluation_result(
            summary=ExternalFactorValidationSummary(
                factor_name="momentum_20d",
                evaluation_engine=EvaluationEngine.ALPHALENS,
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=120,
                effective_sample_count=110,
                coverage_ratio=0.9,
                missing_ratio=0.05,
                ic_mean=0.034,
                rank_ic_mean=0.055,
                ic_std=0.08,
                ic_ir=0.425,
                group_return_spread_mean=0.04,
                source_library="alphalens",
            )
        )
        qlib_result = build_external_factor_evaluation_result(
            summary=ExternalFactorValidationSummary(
                factor_name="momentum_20d",
                evaluation_engine=EvaluationEngine.QLIB,
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=120,
                effective_sample_count=108,
                coverage_ratio=0.9,
                missing_ratio=0.06,
                ic_mean=0.032,
                rank_ic_mean=0.052,
                ic_std=0.08,
                ic_ir=0.4,
                group_return_spread_mean=0.038,
                source_library="qlib",
            )
        )

        comparison_report = build_factor_comparison_report(
            primary_result=alphalens_result,
            additional_results=[qlib_result],
        )

        self.assertEqual(comparison_report.engine_count, 2)
        self.assertFalse(comparison_report.has_engine_disagreement)
        self.assertEqual(
            {result.evaluation_engine for result in comparison_report.engine_results},
            {EvaluationEngine.ALPHALENS, EvaluationEngine.QLIB},
        )


if __name__ == "__main__":
    unittest.main()
