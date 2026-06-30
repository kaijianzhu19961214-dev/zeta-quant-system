import unittest

from pydantic import ValidationError
from quant_contracts import EvaluationEngine
from quant_factor_validation.services.alphalens_evaluation_normalizer import (
    AlphalensMetricSummary,
    build_alphalens_external_summary,
    build_alphalens_factor_evaluation_result,
)


class AlphalensEvaluationNormalizerTest(unittest.TestCase):
    def test_should_map_alphalens_metrics_to_external_summary(self) -> None:
        metrics = AlphalensMetricSummary(
            factor_name="Momentum_20D",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=200,
            effective_sample_count=180,
            mean_information_coefficient=0.034,
            mean_rank_information_coefficient=0.056,
            information_coefficient_std=0.08,
            information_coefficient_ir=0.425,
            mean_quantile_return_spread=0.041,
            source_version="0.4.0",
            source_run_id="alphalens_run_001",
            dataset_code="equity_cn_daily_sample",
            warnings=["Turnover tear sheet is not included yet."],
        )

        summary = build_alphalens_external_summary(metrics=metrics)

        self.assertEqual(summary.factor_name, "momentum_20d")
        self.assertEqual(summary.evaluation_engine, EvaluationEngine.ALPHALENS)
        self.assertEqual(summary.coverage_ratio, 0.9)
        self.assertEqual(summary.missing_ratio, 0.1)
        self.assertEqual(summary.ic_mean, 0.034)
        self.assertEqual(summary.rank_ic_mean, 0.056)
        self.assertEqual(summary.group_return_spread_mean, 0.041)
        self.assertEqual(summary.source_library, "alphalens")
        self.assertEqual(summary.source_run_id, "alphalens_run_001")
        self.assertIn("information_coefficient_ir", summary.source_metric_names)

    def test_should_build_candidate_result_from_alphalens_metrics(self) -> None:
        result = build_alphalens_factor_evaluation_result(
            metrics=AlphalensMetricSummary(
                factor_name="momentum_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=180,
                effective_sample_count=170,
                mean_information_coefficient=0.035,
                mean_rank_information_coefficient=0.06,
                information_coefficient_std=0.08,
                information_coefficient_ir=0.4375,
                mean_quantile_return_spread=0.045,
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.ALPHALENS)
        self.assertEqual(result.report.decision, "candidate_pass")
        self.assertGreater(result.score_card.final_score, 0)
        self.assertTrue(
            any(finding.code == "external_engine_adapter" for finding in result.report.findings)
        )

    def test_should_keep_explicit_coverage_when_supplied(self) -> None:
        metrics = AlphalensMetricSummary(
            factor_name="momentum_20d",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=1,
            sample_count=100,
            effective_sample_count=70,
            coverage_ratio=0.8,
            missing_ratio=0.15,
        )

        summary = build_alphalens_external_summary(metrics=metrics)

        self.assertEqual(summary.coverage_ratio, 0.8)
        self.assertEqual(summary.missing_ratio, 0.15)

    def test_should_reject_alphalens_summary_when_effective_sample_exceeds_total(self) -> None:
        with self.assertRaises(ValidationError):
            AlphalensMetricSummary(
                factor_name="momentum_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=1,
                sample_count=10,
                effective_sample_count=11,
            )


if __name__ == "__main__":
    unittest.main()
