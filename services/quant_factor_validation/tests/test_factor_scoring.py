import unittest

from quant_contracts import (
    EvaluationEngine,
    FactorValidationMetric,
    FactorValidationReport,
)
from quant_factor_validation.services.factor_scoring import (
    build_factor_comparison_report,
    build_factor_evaluation_result,
    build_factor_score_card,
)


class FactorScoringTest(unittest.TestCase):
    def test_should_build_transparent_score_card_from_validation_metrics(self) -> None:
        metrics = FactorValidationMetric(
            factor_name="momentum_20d",
            evaluation_engine=EvaluationEngine.INTERNAL,
            start_date="2026-03-13",
            end_date="2026-03-16",
            forward_days=1,
            sample_count=100,
            effective_sample_count=90,
            coverage_ratio=0.9,
            missing_ratio=0.05,
            ic_ir=0.5,
            rank_ic_mean=0.08,
            group_return_spread_mean=0.04,
            ic_mean=0.03,
        )
        report = FactorValidationReport(
            decision="candidate_pass",
            summary="The factor is ready for candidate review.",
        )

        score_card = build_factor_score_card(metrics=metrics, report=report)

        self.assertEqual(score_card.factor_name, "momentum_20d")
        self.assertEqual(score_card.evaluation_engine, EvaluationEngine.INTERNAL)
        self.assertEqual(score_card.review_decision, "candidate_pass")
        self.assertGreater(score_card.final_score, 0)
        self.assertLessEqual(score_card.final_score, 100)
        self.assertEqual(
            {component.name for component in score_card.score_components},
            {
                "ic_ir_score",
                "ic_mean_score",
                "rank_ic_score",
                "group_return_score",
                "coverage_score",
                "missing_penalty",
                "turnover_penalty",
                "drawdown_penalty",
            },
        )

    def test_should_build_single_engine_comparison_report(self) -> None:
        metrics = FactorValidationMetric(
            factor_name="momentum_20d",
            start_date="2026-03-13",
            end_date="2026-03-16",
            forward_days=1,
            sample_count=10,
            effective_sample_count=8,
        )
        report = FactorValidationReport(
            decision="review_required",
            summary="Manual review is required.",
        )
        score_card = build_factor_score_card(metrics=metrics, report=report)
        evaluation_result = build_factor_evaluation_result(
            metrics=metrics,
            report=report,
            score_card=score_card,
        )

        comparison_report = build_factor_comparison_report(primary_result=evaluation_result)

        self.assertEqual(comparison_report.primary_engine, EvaluationEngine.INTERNAL)
        self.assertEqual(comparison_report.engine_count, 1)
        self.assertFalse(comparison_report.has_engine_disagreement)
        self.assertIn("internal", comparison_report.comparison_summary)


if __name__ == "__main__":
    unittest.main()
