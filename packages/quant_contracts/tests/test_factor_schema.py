import unittest

from pydantic import ValidationError
from quant_contracts import (
    AlgorithmCapability,
    AlgorithmParameterSpec,
    AlgorithmReviewGate,
    AlgorithmSpec,
    ArtifactType,
    AssetClass,
    EvaluationEngine,
    ExternalFactorValidationSummary,
    FactorComparisonReport,
    FactorCalculationRequest,
    FactorDailyValue,
    FactorEvaluationResult,
    FactorFamily,
    FactorGroupReturnPoint,
    FactorMode,
    FactorScoreCard,
    FactorScoreComponent,
    FactorValidationFinding,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationReport,
    FactorValidationRequest,
    PriceMode,
    TaskArtifact,
    TaskRun,
    TaskStatus,
    Timeframe,
)


class FactorSchemaTest(unittest.TestCase):
    def test_should_accept_algorithm_spec_when_payload_is_valid(self) -> None:
        spec = AlgorithmSpec(
            algorithm_id="volatility.egarch",
            display_name="EGARCH volatility model",
            status="planned",
            description="Models asymmetric conditional volatility and leverage effects.",
            source_library="arch",
            capability=AlgorithmCapability(
                asset_classes=[AssetClass.EQUITY, AssetClass.FUTURES],
                factor_modes=[FactorMode.TIME_SERIES],
                factor_families=[FactorFamily.PRICE_VOLUME, FactorFamily.MODEL],
                timeframes=[Timeframe.DAY_1],
                output_kinds=["volatility", "diagnostics"],
            ),
            parameters=[
                AlgorithmParameterSpec(
                    name="p",
                    value_type="integer",
                    description="ARCH lag order.",
                    default_value=1,
                    minimum=1,
                    maximum=5,
                )
            ],
            tags=[" volatility ", " leverage_effect "],
            review_gates=[
                AlgorithmReviewGate(
                    gate_id="validation_evidence",
                    category="validation",
                    title="Validation evidence",
                    description="IC, Rank IC, decay, and portfolio diagnostics are required before promotion.",
                    status="missing",
                )
            ],
        )

        self.assertEqual(spec.algorithm_id, "volatility.egarch")
        self.assertEqual(spec.parameters[0].name, "p")
        self.assertEqual(spec.tags, ["volatility", "leverage_effect"])
        self.assertEqual(spec.review_gates[0].gate_id, "validation_evidence")

    def test_should_reject_available_algorithm_when_required_review_gate_is_missing(self) -> None:
        with self.assertRaises(ValidationError):
            AlgorithmSpec(
                algorithm_id="technical.example",
                display_name="Example factor",
                status="available",
                description="Example algorithm with an incomplete review gate.",
                capability=AlgorithmCapability(
                    asset_classes=[AssetClass.EQUITY],
                    factor_modes=[FactorMode.CROSS_SECTIONAL],
                    factor_families=[FactorFamily.PRICE_VOLUME],
                    timeframes=[Timeframe.DAY_1],
                    output_kinds=["factor_values"],
                ),
                review_gates=[
                    AlgorithmReviewGate(
                        gate_id="leakage_audit",
                        category="leakage",
                        title="Leakage audit",
                        description="Future-function and tradability checks must be documented.",
                        status="missing",
                    )
                ],
            )

    def test_should_normalize_factor_request_when_payload_is_valid(self) -> None:
        request = FactorCalculationRequest(
            factor_name="Momentum_20D",
            algorithm_id="Technical.Momentum",
            symbols=[" 000001.sz ", "000651.SZ"],
            start="2026-01-01",
            end="2026-03-13",
        )

        self.assertEqual(request.factor_name, "momentum_20d")
        self.assertEqual(request.algorithm_id, "technical.momentum")
        self.assertEqual(request.symbols, ["000001.SZ", "000651.SZ"])
        self.assertEqual(request.asset_class, AssetClass.EQUITY)
        self.assertEqual(request.factor_mode, FactorMode.CROSS_SECTIONAL)
        self.assertEqual(request.factor_family, FactorFamily.PRICE_VOLUME)
        self.assertEqual(request.timeframe, Timeframe.DAY_1)

    def test_should_reject_non_daily_timeframe_for_mvp_factor_request(self) -> None:
        with self.assertRaises(ValidationError):
            FactorCalculationRequest(
                factor_name="momentum_20d",
                symbols=["000001.SZ"],
                start="2026-01-01",
                end="2026-03-13",
                timeframe=Timeframe.MINUTE_1,
            )

    def test_should_require_batch_id_when_qfq_price_mode_is_used(self) -> None:
        with self.assertRaises(ValidationError):
            FactorCalculationRequest(
                factor_name="momentum_20d",
                symbols=["000001.SZ"],
                start="2026-01-01",
                end="2026-03-13",
                price_mode=PriceMode.QFQ,
            )

    def test_should_normalize_factor_daily_value_symbol(self) -> None:
        value = FactorDailyValue(
            symbol=" 000001.sz ",
            trade_date="2026-03-13",
            factor_name="momentum_20d",
            factor_value="0.15",
        )

        self.assertEqual(value.symbol, "000001.SZ")
        self.assertEqual(str(value.factor_value), "0.15")

    def test_should_accept_factor_validation_request_when_factor_values_match(self) -> None:
        request = FactorValidationRequest(
            factor_name="momentum_20d",
            factor_values=[
                FactorDailyValue(
                    symbol="000001.SZ",
                    trade_date="2026-03-13",
                    factor_name="momentum_20d",
                    factor_value="0.15",
                )
            ],
            market_start="2026-03-13",
            market_end="2026-03-16",
        )

        self.assertEqual(request.forward_days, 1)
        self.assertEqual(request.group_count, 5)
        self.assertEqual(request.evaluation_engine, EvaluationEngine.INTERNAL)
        self.assertEqual(request.timeframe, Timeframe.DAY_1)

    def test_should_accept_factor_group_return_point_when_payload_is_valid(self) -> None:
        point = FactorGroupReturnPoint(
            trade_date="2026-03-13",
            group_index=5,
            group_count=5,
            sample_size=20,
            average_forward_return=0.032,
        )

        self.assertEqual(point.group_index, 5)
        self.assertEqual(point.group_count, 5)
        self.assertEqual(point.sample_size, 20)

    def test_should_reject_factor_validation_request_when_factor_name_mismatches(self) -> None:
        with self.assertRaises(ValidationError):
            FactorValidationRequest(
                factor_name="momentum_20d",
                factor_values=[
                    FactorDailyValue(
                        symbol="000001.SZ",
                        trade_date="2026-03-13",
                        factor_name="reversal_5d",
                        factor_value="0.15",
                    )
                ],
                market_start="2026-03-13",
                market_end="2026-03-16",
            )

    def test_should_reject_factor_validation_request_when_classification_mismatches(self) -> None:
        with self.assertRaises(ValidationError):
            FactorValidationRequest(
                factor_name="momentum_20d",
                factor_values=[
                    FactorDailyValue(
                        symbol="000001.SZ",
                        trade_date="2026-03-13",
                        factor_name="momentum_20d",
                        factor_value="0.15",
                        asset_class=AssetClass.FUTURES,
                    )
                ],
                market_start="2026-03-13",
                market_end="2026-03-16",
                asset_class=AssetClass.EQUITY,
            )

    def test_should_accept_factor_validation_report_when_payload_is_valid(self) -> None:
        report = FactorValidationReport(
            decision="review_required",
            summary="Manual review is required.",
            findings=[
                FactorValidationFinding(
                    severity="info",
                    code="manual_review_required",
                    message="Sample size is not enough for an automatic decision.",
                )
            ],
            recommended_actions=["Expand the validation sample."],
        )

        self.assertEqual(report.decision, "review_required")
        self.assertEqual(report.findings[0].code, "manual_review_required")

    def test_should_accept_factor_score_card_when_payload_is_valid(self) -> None:
        score_card = FactorScoreCard(
            factor_name="momentum_20d",
            evaluation_engine=EvaluationEngine.INTERNAL,
            final_score=72.5,
            review_decision="candidate_pass",
            score_components=[
                FactorScoreComponent(
                    name="rank_ic_score",
                    raw_value=0.08,
                    score=20.0,
                    max_score=25.0,
                    reason="Rank IC is above the first-stage review threshold.",
                )
            ],
            warnings=["Turnover has not been measured in this validation run."],
        )

        self.assertEqual(score_card.evaluation_engine, EvaluationEngine.INTERNAL)
        self.assertEqual(score_card.score_components[0].name, "rank_ic_score")

    def test_should_accept_factor_comparison_report_when_payload_is_valid(self) -> None:
        metrics = FactorValidationMetric(
            factor_name="momentum_20d",
            start_date="2026-03-13",
            end_date="2026-03-16",
            forward_days=1,
            sample_count=3,
            effective_sample_count=3,
        )
        evaluation_result = FactorEvaluationResult(
            factor_name="momentum_20d",
            evaluation_engine=EvaluationEngine.INTERNAL,
            metrics=metrics,
        )
        comparison_report = FactorComparisonReport(
            factor_name="momentum_20d",
            primary_engine=EvaluationEngine.INTERNAL,
            engine_results=[evaluation_result],
            engine_count=1,
            comparison_summary="Only the internal validation engine has run.",
        )

        self.assertFalse(comparison_report.has_engine_disagreement)
        self.assertEqual(comparison_report.engine_results[0].evaluation_engine, EvaluationEngine.INTERNAL)

    def test_should_accept_external_factor_validation_summary_when_payload_is_valid(self) -> None:
        summary = ExternalFactorValidationSummary(
            factor_name="TSMOM_20D",
            asset_class=AssetClass.FUTURES,
            factor_mode=FactorMode.TIME_SERIES,
            factor_family=FactorFamily.PRICE_VOLUME,
            evaluation_engine=EvaluationEngine.VECTORBT,
            start_date="2026-01-01",
            end_date="2026-03-13",
            forward_days=5,
            sample_count=120,
            effective_sample_count=110,
            coverage_ratio=0.92,
            missing_ratio=0.03,
            ic_mean=0.04,
            rank_ic_mean=0.05,
            ic_std=0.08,
            ic_ir=0.5,
            group_return_spread_mean=0.03,
            source_library="vectorbt",
            source_version="0.28.0",
            source_metric_names=["mean_ic", "rank_ic", "group_return_spread"],
            warnings=["Turnover is not included in this external summary."],
        )

        self.assertEqual(summary.factor_name, "tsmom_20d")
        self.assertEqual(summary.evaluation_engine, EvaluationEngine.VECTORBT)
        self.assertEqual(summary.source_metric_names[0], "mean_ic")

    def test_should_reject_external_summary_when_engine_is_internal(self) -> None:
        with self.assertRaises(ValidationError):
            ExternalFactorValidationSummary(
                factor_name="momentum_20d",
                evaluation_engine=EvaluationEngine.INTERNAL,
                start_date="2026-03-13",
                end_date="2026-03-16",
                forward_days=1,
                sample_count=10,
                effective_sample_count=8,
                source_library="internal",
            )

    def test_should_accept_factor_validation_manifest_when_payload_is_valid(self) -> None:
        manifest = FactorValidationManifest(
            manifest_id="manifest_run_1",
            task_run=TaskRun(
                task_id="run_1",
                task_type="factor_validation",
                task_name="momentum_20d_validation",
                status=TaskStatus.SUCCEEDED,
            ),
            artifacts=[
                TaskArtifact(
                    artifact_id="artifact_report_1",
                    task_id="run_1",
                    artifact_type=ArtifactType.VALIDATION_REPORT,
                    object_key="factor_validation/momentum_20d/run_1/validation_report.json",
                    metadata={"decision": "review_required"},
                )
            ],
        )

        self.assertEqual(manifest.persistence_status, "not_persisted")
        self.assertEqual(manifest.artifacts[0].artifact_type, ArtifactType.VALIDATION_REPORT)


if __name__ == "__main__":
    unittest.main()
