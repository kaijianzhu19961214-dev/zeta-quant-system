import unittest

from pydantic import ValidationError
from quant_contracts import AssetClass, EvaluationEngine, FactorFamily, FactorMode
from quant_factor_validation.services.vectorbt_evaluation_normalizer import (
    VectorbtMetricPayload,
    VectorbtMetricSummary,
    build_vectorbt_external_summary,
    build_vectorbt_factor_evaluation_result,
    build_vectorbt_metric_summary_from_payload,
    run_vectorbt_payload_evaluation,
)


class VectorbtEvaluationNormalizerTest(unittest.TestCase):
    def test_should_map_vectorbt_payload_aliases_to_metric_summary(self) -> None:
        payload = VectorbtMetricPayload(
            factor_name="TSMOM_20D",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=120,
            effective_sample_count=110,
            metric_values={
                "Total Return": "18%",
                "Annualized Return": 0.26,
                "Sharpe Ratio": 1.35,
                "Max Drawdown": "-8%",
                "turnover": "35%",
                "Total Trades": 42,
                "Win Rate": "57%",
                "signal_coverage": "91.67%",
            },
            source_version="0.28.0",
            portfolio_name="tsmom_20d_portfolio",
            parameter_set_id="lookback_20_hold_5",
        )

        metrics = build_vectorbt_metric_summary_from_payload(payload=payload)

        self.assertEqual(metrics.factor_name, "tsmom_20d")
        self.assertEqual(metrics.asset_class, AssetClass.FUTURES)
        self.assertEqual(metrics.factor_mode, FactorMode.TIME_SERIES)
        self.assertEqual(metrics.factor_family, FactorFamily.PRICE_VOLUME)
        self.assertEqual(metrics.total_return, 0.18)
        self.assertEqual(metrics.annualized_return, 0.26)
        self.assertEqual(metrics.sharpe_ratio, 1.35)
        self.assertEqual(metrics.max_drawdown, -0.08)
        self.assertEqual(metrics.turnover_ratio, 0.35)
        self.assertEqual(metrics.trade_count, 42)
        self.assertEqual(metrics.win_rate, 0.57)
        self.assertAlmostEqual(metrics.coverage_ratio, 0.9167)

    def test_should_run_vectorbt_payload_evaluation(self) -> None:
        result = run_vectorbt_payload_evaluation(
            payload=VectorbtMetricPayload(
                factor_name="tsmom_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=120,
                effective_sample_count=110,
                metric_values={
                    "annualized_return": 0.24,
                    "sharpe": 1.2,
                    "max_dd": -0.09,
                    "turnover_ratio": 0.4,
                },
                parameter_set_id="lookback_20_hold_5",
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.VECTORBT)
        self.assertEqual(result.metrics.asset_class, AssetClass.FUTURES)
        self.assertEqual(result.metrics.factor_mode, FactorMode.TIME_SERIES)
        self.assertEqual(result.metrics.group_return_spread_mean, 0.24)
        self.assertGreater(result.score_card.final_score, 0)
        self.assertIn("vectorbt", result.report.findings[-1].message)

    def test_should_map_vectorbt_summary_to_external_summary_with_notes(self) -> None:
        summary = build_vectorbt_external_summary(
            metrics=VectorbtMetricSummary(
                factor_name="tsmom_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=100,
                effective_sample_count=90,
                total_return=0.18,
                annualized_return=0.26,
                sharpe_ratio=1.35,
                sortino_ratio=1.8,
                max_drawdown=-0.08,
                turnover_ratio=0.35,
                trade_count=42,
                win_rate=0.57,
                portfolio_name="tsmom_20d_portfolio",
                parameter_set_id="lookback_20_hold_5",
            )
        )

        self.assertEqual(summary.evaluation_engine, EvaluationEngine.VECTORBT)
        self.assertEqual(summary.coverage_ratio, 0.9)
        self.assertEqual(summary.missing_ratio, 0.1)
        self.assertEqual(summary.group_return_spread_mean, 0.26)
        self.assertIn("vectorbt_sharpe_ratio", summary.source_metric_names)
        self.assertIn("vectorbt_sharpe_ratio=1.35", summary.notes)
        self.assertIn("vectorbt_parameter_set_id=lookback_20_hold_5", summary.notes)

    def test_should_build_candidate_result_from_vectorbt_summary(self) -> None:
        result = build_vectorbt_factor_evaluation_result(
            metrics=VectorbtMetricSummary(
                factor_name="tsmom_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=5,
                sample_count=120,
                effective_sample_count=110,
                annualized_return=0.22,
                sharpe_ratio=1.1,
            )
        )

        self.assertEqual(result.evaluation_engine, EvaluationEngine.VECTORBT)
        self.assertEqual(result.metrics.group_return_spread_mean, 0.22)
        self.assertGreater(result.score_card.final_score, 0)

    def test_should_reject_vectorbt_payload_when_effective_sample_exceeds_total(self) -> None:
        with self.assertRaises(ValidationError):
            VectorbtMetricPayload(
                factor_name="tsmom_20d",
                start_date="2026-01-01",
                end_date="2026-03-13",
                forward_days=1,
                sample_count=10,
                effective_sample_count=11,
            )

    def test_should_reject_vectorbt_payload_when_metric_value_is_not_numeric(self) -> None:
        payload = VectorbtMetricPayload(
            factor_name="tsmom_20d",
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=1,
            sample_count=10,
            effective_sample_count=8,
            metric_values={"annualized_return": "not-a-number"},
        )

        with self.assertRaises(ValueError):
            build_vectorbt_metric_summary_from_payload(payload=payload)


if __name__ == "__main__":
    unittest.main()
