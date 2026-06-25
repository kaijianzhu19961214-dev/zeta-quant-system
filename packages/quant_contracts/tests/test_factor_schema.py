import unittest

from pydantic import ValidationError
from quant_contracts import (
    ArtifactType,
    FactorCalculationRequest,
    FactorDailyValue,
    FactorValidationFinding,
    FactorValidationManifest,
    FactorValidationReport,
    FactorValidationRequest,
    PriceMode,
    TaskArtifact,
    TaskRun,
    TaskStatus,
    Timeframe,
)


class FactorSchemaTest(unittest.TestCase):
    def test_should_normalize_factor_request_when_payload_is_valid(self) -> None:
        request = FactorCalculationRequest(
            factor_name="Momentum_20D",
            symbols=[" 000001.sz ", "000651.SZ"],
            start="2026-01-01",
            end="2026-03-13",
        )

        self.assertEqual(request.factor_name, "momentum_20d")
        self.assertEqual(request.symbols, ["000001.SZ", "000651.SZ"])
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
        self.assertEqual(request.timeframe, Timeframe.DAY_1)

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
