import unittest

from pydantic import ValidationError
from quant_contracts import EvaluationEngine, FactorFamily
from quant_factor_validation.services.qlib_evaluation_normalizer import (
    QlibMetricPayload,
    QlibMetricSummary,
    build_qlib_external_summary,
    build_qlib_factor_evaluation_result,
    build_qlib_metric_summary_from_payload,
    run_qlib_payload_evaluation,
)


class QlibEvaluationNormalizerTest(unittest.TestCase):
    def test_should_map_qlib_payload_aliases_to_metric_summary(self) -> None:
        payload = QlibMetricPayload(
            factor_name="Qlib_Model_Score",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=200,
            effective_sample_count=176,
            metric_values={
                "IC": "4.2%",
                "Rank IC": 0.061,
                "ICIR": 0.5,
                "long_short_return": 0.038,
                "coverage_ratio": "88%",
                "missing_ratio": "12%",
                "quantiles": 5,
            },
            source_version="0.9.0",
            recorder_id="recorder_001",
            experiment_name="alpha158_lgbm",
        )

        metrics = build_qlib_metric_summary_from_payload(payload=payload)

        self.assertEqual(metrics.factor_name, "qlib_model_score")
        self.assertEqual(metrics.factor_family, FactorFamily.MODEL)
        self.assertEqual(metrics.mean_information_coefficient, 0.042)
        self.assertEqual(metrics.mean_rank_information_coefficient, 0.061)
        self.assertEqual(metrics.information_coefficient_ir, 0.5)
        self.assertEqual(metrics.mean_long_short_return_spread, 0.038)
        self.assertEqual(metrics.coverage_ratio, 0.88)
        self.assertEqual(metrics.missing_ratio, 0.12)
        self.assertEqual(metrics.source_run_id, "recorder_001")

    def test_should_run_qlib_payload_evaluation(self) -> None:
        result = run_qlib_payload_evaluation(
            payload=QlibMetricPayload(
                factor_name="qlib_model_score",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=180,
                effective_sample_count=165,
                metric_values={
                    "ic_mean": 0.036,
                    "rank_ic_mean": 0.058,
                    "ic_std": 0.08,
                    "icir": 0.45,
                    "return_spread": 0.04,
                },
                recorder_id="recorder_002",
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.QLIB)
        self.assertEqual(result.metrics.factor_family, FactorFamily.MODEL)
        self.assertEqual(result.metrics.ic_mean, 0.036)
        self.assertEqual(result.report.decision, "candidate_pass")
        self.assertGreater(result.score_card.final_score, 0)

    def test_should_map_qlib_summary_to_external_summary(self) -> None:
        summary = build_qlib_external_summary(
            metrics=QlibMetricSummary(
                factor_name="qlib_model_score",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=100,
                effective_sample_count=90,
                mean_information_coefficient=0.03,
                mean_rank_information_coefficient=0.052,
                information_coefficient_std=0.08,
                information_coefficient_ir=0.4,
                mean_long_short_return_spread=0.035,
                recorder_id="recorder_003",
                experiment_name="alpha360_lgbm",
            )
        )

        self.assertEqual(summary.evaluation_engine, EvaluationEngine.QLIB)
        self.assertEqual(summary.coverage_ratio, 0.9)
        self.assertEqual(summary.missing_ratio, 0.1)
        self.assertEqual(summary.group_return_spread_mean, 0.035)
        self.assertIn("qlib_icir", summary.source_metric_names)
        self.assertIn("qlib_recorder_id=recorder_003", summary.notes)

    def test_should_build_candidate_result_from_qlib_summary(self) -> None:
        result = build_qlib_factor_evaluation_result(
            metrics=QlibMetricSummary(
                factor_name="qlib_model_score",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=180,
                effective_sample_count=170,
                mean_information_coefficient=0.035,
                mean_rank_information_coefficient=0.06,
                information_coefficient_std=0.08,
                information_coefficient_ir=0.4375,
                mean_long_short_return_spread=0.045,
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.QLIB)
        self.assertEqual(result.report.decision, "candidate_pass")
        self.assertGreater(result.score_card.final_score, 0)

    def test_should_reject_qlib_payload_when_effective_sample_exceeds_total(self) -> None:
        with self.assertRaises(ValidationError):
            QlibMetricPayload(
                factor_name="qlib_model_score",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=1,
                sample_count=10,
                effective_sample_count=11,
            )

    def test_should_reject_qlib_payload_when_metric_value_is_not_numeric(self) -> None:
        payload = QlibMetricPayload(
            factor_name="qlib_model_score",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=1,
            sample_count=10,
            effective_sample_count=8,
            metric_values={"IC": "not-a-number"},
        )

        with self.assertRaises(ValueError):
            build_qlib_metric_summary_from_payload(payload=payload)


if __name__ == "__main__":
    unittest.main()
