import unittest

from pydantic import ValidationError
from quant_contracts import EvaluationEngine
from quant_factor_validation.services.alphalens_evaluation_normalizer import (
    AlphalensMetricPayload,
    AlphalensMetricSummary,
    build_alphalens_external_summary,
    build_alphalens_factor_evaluation_result,
    build_alphalens_metric_summary_from_payload,
    run_alphalens_payload_evaluation,
)


class AlphalensEvaluationNormalizerTest(unittest.TestCase):
    def test_should_map_alphalens_payload_aliases_to_metric_summary(self) -> None:
        payload = AlphalensMetricPayload(
            factor_name="Momentum_20D",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=200,
            effective_sample_count=180,
            metric_values={
                "mean_ic": "3.4%",
                "rank_ic_mean": 0.056,
                "ic_std": 0.08,
                "ic_ir": 0.425,
                "mean_quantile_returns_spread": 0.041,
                "coverage": "90%",
                "missing": "10%",
                "quantiles": 5,
            },
            source_version="0.4.0",
            source_run_id="alphalens_payload_001",
        )

        metrics = build_alphalens_metric_summary_from_payload(payload=payload)

        self.assertEqual(metrics.factor_name, "momentum_20d")
        self.assertEqual(metrics.mean_information_coefficient, 0.034)
        self.assertEqual(metrics.mean_rank_information_coefficient, 0.056)
        self.assertEqual(metrics.coverage_ratio, 0.9)
        self.assertEqual(metrics.missing_ratio, 0.1)
        self.assertEqual(metrics.group_count, 5)
        self.assertEqual(metrics.source_run_id, "alphalens_payload_001")

    def test_should_run_alphalens_payload_evaluation(self) -> None:
        result = run_alphalens_payload_evaluation(
            payload=AlphalensMetricPayload(
                factor_name="momentum_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=180,
                effective_sample_count=170,
                metric_values={
                    "IC Mean": 0.035,
                    "Rank IC Mean": 0.06,
                    "IC Std.": 0.08,
                    "IC IR": 0.4375,
                    "mean_return_spread": 0.045,
                },
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.ALPHALENS)
        self.assertEqual(result.metrics.ic_mean, 0.035)
        self.assertEqual(result.report.decision, "candidate_pass")
        self.assertGreater(result.score_card.final_score, 0)

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

    def test_should_reject_alphalens_payload_when_metric_value_is_not_numeric(self) -> None:
        payload = AlphalensMetricPayload(
            factor_name="momentum_20d",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=1,
            sample_count=10,
            effective_sample_count=8,
            metric_values={"mean_ic": "not-a-number"},
        )

        with self.assertRaises(ValueError):
            build_alphalens_metric_summary_from_payload(payload=payload)


if __name__ == "__main__":
    unittest.main()
