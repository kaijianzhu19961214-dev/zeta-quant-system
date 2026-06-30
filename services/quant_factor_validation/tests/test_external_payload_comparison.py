import unittest

from pydantic import ValidationError
from quant_contracts import EvaluationEngine
from quant_factor_validation.services.alphalens_evaluation_normalizer import AlphalensMetricPayload
from quant_factor_validation.services.external_payload_comparison import (
    ExternalPayloadEvaluationSet,
    build_external_payload_comparison_report,
    build_external_payload_evaluation_results,
)
from quant_factor_validation.services.qlib_evaluation_normalizer import QlibMetricPayload
from quant_factor_validation.services.vectorbt_evaluation_normalizer import VectorbtMetricPayload


class ExternalPayloadComparisonTest(unittest.TestCase):
    def test_should_build_multi_engine_payload_comparison_report(self) -> None:
        payload_set = ExternalPayloadEvaluationSet(
            factor_name="momentum_20d",
            primary_engine=EvaluationEngine.ALPHALENS,
            alphalens_payloads=[
                AlphalensMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=180,
                    effective_sample_count=170,
                    metric_values={
                        "mean_ic": 0.035,
                        "rank_ic_mean": 0.06,
                        "ic_std": 0.08,
                        "ic_ir": 0.4375,
                        "mean_return_spread": 0.045,
                    },
                )
            ],
            qlib_payloads=[
                QlibMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=180,
                    effective_sample_count=166,
                    metric_values={
                        "ic_mean": 0.033,
                        "rank_ic_mean": 0.055,
                        "ic_std": 0.08,
                        "icir": 0.4125,
                        "return_spread": 0.04,
                    },
                    recorder_id="qlib_recorder_001",
                )
            ],
            vectorbt_payloads=[
                VectorbtMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=120,
                    effective_sample_count=110,
                    metric_values={
                        "annualized_return": 0.22,
                        "sharpe": 1.1,
                        "max_dd": -0.08,
                    },
                    parameter_set_id="lookback_20_hold_5",
                )
            ],
        )

        comparison_report = build_external_payload_comparison_report(payload_set=payload_set)

        self.assertEqual(comparison_report.factor_name, "momentum_20d")
        self.assertEqual(comparison_report.primary_engine, EvaluationEngine.ALPHALENS)
        self.assertEqual(comparison_report.engine_count, 3)
        self.assertTrue(comparison_report.has_engine_disagreement)
        self.assertEqual(
            {result.evaluation_engine for result in comparison_report.engine_results},
            {EvaluationEngine.ALPHALENS, EvaluationEngine.QLIB, EvaluationEngine.VECTORBT},
        )

    def test_should_build_external_payload_evaluation_results(self) -> None:
        payload_set = ExternalPayloadEvaluationSet(
            factor_name="momentum_20d",
            primary_engine=EvaluationEngine.QLIB,
            qlib_payloads=[
                QlibMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=100,
                    effective_sample_count=90,
                    metric_values={"IC": 0.03},
                )
            ],
        )

        results = build_external_payload_evaluation_results(payload_set=payload_set)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].evaluation_engine, EvaluationEngine.QLIB)

    def test_should_reject_payload_set_without_payloads(self) -> None:
        with self.assertRaises(ValidationError):
            ExternalPayloadEvaluationSet(factor_name="momentum_20d")

    def test_should_reject_payload_set_when_factor_name_mismatches(self) -> None:
        with self.assertRaises(ValidationError):
            ExternalPayloadEvaluationSet(
                factor_name="momentum_20d",
                alphalens_payloads=[
                    AlphalensMetricPayload(
                        factor_name="reversal_5d",
                        start_date="2026-01-01",
                        end_date="2026-03-13",
                        forward_days=5,
                        sample_count=10,
                        effective_sample_count=8,
                    )
                ],
            )

    def test_should_reject_comparison_when_primary_payload_is_missing(self) -> None:
        payload_set = ExternalPayloadEvaluationSet(
            factor_name="momentum_20d",
            primary_engine=EvaluationEngine.VECTORBT,
            alphalens_payloads=[
                AlphalensMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=10,
                    effective_sample_count=8,
                )
            ],
        )

        with self.assertRaises(ValueError):
            build_external_payload_comparison_report(payload_set=payload_set)


if __name__ == "__main__":
    unittest.main()
