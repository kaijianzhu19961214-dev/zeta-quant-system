from datetime import date
import unittest

from quant_contracts import FactorValidationMetric, PriceMode
from quant_factor_validation.services import build_validation_report


class ValidationReportTest(unittest.TestCase):
    def test_should_mark_insufficient_data_when_no_effective_sample(self) -> None:
        report = build_validation_report(
            metrics=_make_metrics(
                effective_sample_count=0,
                coverage_ratio=0,
                ic_mean=None,
                rank_ic_mean=None,
                ic_ir=None,
            )
        )

        self.assertEqual(report.decision, "insufficient_data")
        self.assertEqual(report.findings[0].code, "no_effective_sample")

    def test_should_mark_candidate_reject_when_sample_is_enough_but_signal_is_weak(self) -> None:
        report = build_validation_report(
            metrics=_make_metrics(
                effective_sample_count=120,
                coverage_ratio=0.95,
                ic_mean=0.005,
                rank_ic_mean=0.01,
                ic_ir=0.4,
            )
        )

        self.assertEqual(report.decision, "candidate_reject")
        self.assertEqual(report.findings[0].code, "weak_ic_signal")

    def test_should_mark_candidate_pass_when_sample_and_signal_are_enough(self) -> None:
        report = build_validation_report(
            metrics=_make_metrics(
                effective_sample_count=120,
                coverage_ratio=0.95,
                ic_mean=0.04,
                rank_ic_mean=0.07,
                ic_ir=0.5,
            )
        )

        self.assertEqual(report.decision, "candidate_pass")
        self.assertIn("robustness", report.recommended_actions[0])


def _make_metrics(
    *,
    effective_sample_count: int,
    coverage_ratio: float | None,
    ic_mean: float | None,
    rank_ic_mean: float | None,
    ic_ir: float | None,
) -> FactorValidationMetric:
    return FactorValidationMetric(
        factor_name="momentum_20d",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        forward_days=1,
        sample_count=120,
        effective_sample_count=effective_sample_count,
        coverage_ratio=coverage_ratio,
        missing_ratio=0,
        ic_mean=ic_mean,
        rank_ic_mean=rank_ic_mean,
        ic_std=0.08,
        ic_ir=ic_ir,
        universe_name="all_a",
        price_mode=PriceMode.QFQ,
        dataset_code="a_share_1d",
        batch_id="qfq_20260331",
        validation_version="v1",
        run_id="run_validation_test",
    )


if __name__ == "__main__":
    unittest.main()
