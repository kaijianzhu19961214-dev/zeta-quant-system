from datetime import date
import unittest

from quant_contracts import (
    ArtifactType,
    FactorDailyValue,
    FactorIcPoint,
    FactorValidationFinding,
    FactorValidationMetric,
    FactorValidationReport,
    FactorValidationRequest,
    PriceMode,
)
from quant_factor_validation.services import build_validation_manifest


class ValidationManifestTest(unittest.TestCase):
    def test_should_build_not_persisted_manifest_when_validation_finishes(self) -> None:
        manifest = build_validation_manifest(
            request=FactorValidationRequest(
                factor_name="momentum_20d",
                factor_values=[_make_factor_value_stub()],
                market_start="2026-01-01",
                market_end="2026-03-31",
                run_id="validation run 1",
            ),
            metrics=_make_metrics(),
            report=FactorValidationReport(
                decision="review_required",
                summary="Manual review is required.",
                findings=[
                    FactorValidationFinding(
                        severity="info",
                        code="manual_review_required",
                        message="Sample size is not enough for an automatic decision.",
                    )
                ],
            ),
            ic_series=[
                FactorIcPoint(
                    trade_date=date(2026, 3, 13),
                    sample_size=3,
                    ic=0.1,
                    rank_ic=0.2,
                )
            ],
        )

        self.assertEqual(manifest.persistence_status, "not_persisted")
        self.assertEqual(manifest.task_run.task_type, "factor_validation")
        self.assertEqual(manifest.task_run.output_summary["decision"], "review_required")
        self.assertEqual(manifest.artifacts[0].artifact_type, ArtifactType.VALIDATION_REPORT)
        self.assertEqual(
            manifest.artifacts[0].object_key,
            "factor_validation/momentum_20d/validation_run_1/validation_report.json",
        )
        self.assertEqual(manifest.artifacts[2].metadata["row_count"], 1)


def _make_factor_value_stub() -> FactorDailyValue:
    return FactorDailyValue(
        symbol="000001.SZ",
        trade_date="2026-03-13",
        factor_name="momentum_20d",
        factor_value="0.1",
    )


def _make_metrics() -> FactorValidationMetric:
    return FactorValidationMetric(
        factor_name="momentum_20d",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 3, 31),
        forward_days=1,
        sample_count=120,
        effective_sample_count=90,
        coverage_ratio=0.75,
        missing_ratio=0.01,
        ic_mean=0.02,
        rank_ic_mean=0.04,
        ic_ir=0.2,
        universe_name="all_a",
        price_mode=PriceMode.QFQ,
        dataset_code="a_share_1d",
        batch_id="qfq_20260331",
        validation_version="v1",
        run_id="validation run 1",
    )


if __name__ == "__main__":
    unittest.main()
