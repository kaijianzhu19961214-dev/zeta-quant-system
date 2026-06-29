from datetime import date
from hashlib import sha256
import json
import unittest

from quant_contracts import (
    FactorDailyValue,
    FactorGroupReturnPoint,
    FactorIcPoint,
    FactorValidationFinding,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationReport,
    FactorValidationRequest,
)
from quant_factor_validation.services import (
    build_validation_artifact_payloads,
    build_validation_manifest,
    enrich_manifest_with_artifact_payloads,
)


class ValidationArtifactsTest(unittest.TestCase):
    def test_should_materialize_deterministic_json_payloads(self) -> None:
        manifest = _make_manifest()
        metrics = _make_metrics()
        report = _make_report()
        ic_series = _make_ic_series()
        group_returns = _make_group_returns()

        payloads = build_validation_artifact_payloads(
            manifest=manifest,
            metrics=metrics,
            report=report,
            ic_series=ic_series,
            group_returns=group_returns,
        )

        self.assertEqual(len(payloads), 4)
        self.assertEqual(
            {payload.schema_version for payload in payloads},
            {
                "factor_validation_report.v1",
                "factor_validation_metrics.v1",
                "factor_ic_series.v1",
                "factor_group_returns.v1",
            },
        )
        self.assertTrue(all(payload.content_type == "application/json" for payload in payloads))
        self.assertTrue(all(payload.size_bytes == len(payload.body) for payload in payloads))
        self.assertTrue(
            all(payload.sha256 == sha256(payload.body).hexdigest() for payload in payloads)
        )

        report_payload = next(
            payload for payload in payloads if payload.schema_version == "factor_validation_report.v1"
        )
        self.assertEqual(
            json.loads(report_payload.body.decode("utf-8"))["decision"],
            "review_required",
        )

    def test_should_enrich_manifest_with_payload_metadata(self) -> None:
        manifest = _make_manifest()
        payloads = build_validation_artifact_payloads(
            manifest=manifest,
            metrics=_make_metrics(),
            report=_make_report(),
            ic_series=_make_ic_series(),
            group_returns=_make_group_returns(),
        )

        enriched_manifest = enrich_manifest_with_artifact_payloads(
            manifest=manifest,
            artifact_payloads=payloads,
        )

        first_artifact = enriched_manifest.artifacts[0]
        first_payload = payloads[0]
        self.assertEqual(first_artifact.file_size_bytes, first_payload.size_bytes)
        self.assertEqual(first_artifact.metadata["content_type"], "application/json")
        self.assertEqual(first_artifact.metadata["sha256"], first_payload.sha256)
        self.assertEqual(manifest.artifacts[0].file_size_bytes, None)

    def test_should_reject_artifact_without_schema_version(self) -> None:
        manifest = _make_manifest()
        broken_artifact = manifest.artifacts[0].model_copy(
            update={"metadata": {"row_count": 1}},
        )
        broken_manifest = manifest.model_copy(
            update={"artifacts": [broken_artifact, *manifest.artifacts[1:]]},
        )

        with self.assertRaisesRegex(ValueError, "schema_version"):
            build_validation_artifact_payloads(
                manifest=broken_manifest,
                metrics=_make_metrics(),
                report=_make_report(),
                ic_series=_make_ic_series(),
                group_returns=_make_group_returns(),
            )

    def test_should_reject_artifact_without_object_key(self) -> None:
        manifest = _make_manifest()
        broken_artifact = manifest.artifacts[0].model_copy(update={"object_key": None})
        broken_manifest = manifest.model_copy(
            update={"artifacts": [broken_artifact, *manifest.artifacts[1:]]},
        )

        with self.assertRaisesRegex(ValueError, "object_key"):
            build_validation_artifact_payloads(
                manifest=broken_manifest,
                metrics=_make_metrics(),
                report=_make_report(),
                ic_series=_make_ic_series(),
                group_returns=_make_group_returns(),
            )


def _make_manifest() -> FactorValidationManifest:
    return build_validation_manifest(
        request=FactorValidationRequest(
            factor_name="momentum_20d",
            factor_values=[_make_factor_value()],
            market_start="2026-01-01",
            market_end="2026-03-31",
            run_id="validation run 1",
        ),
        metrics=_make_metrics(),
        report=_make_report(),
        ic_series=_make_ic_series(),
        group_returns=_make_group_returns(),
    )


def _make_factor_value() -> FactorDailyValue:
    return FactorDailyValue(
        symbol="000001.SZ",
        trade_date=date(2026, 3, 13),
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
        group_count=5,
        group_return_spread_mean=0.03,
        dataset_code="a_share_1d",
        batch_id="qfq_20260331",
        validation_version="v1",
        run_id="validation run 1",
    )


def _make_report() -> FactorValidationReport:
    return FactorValidationReport(
        decision="review_required",
        summary="Manual review is required.",
        findings=[
            FactorValidationFinding(
                severity="info",
                code="manual_review_required",
                message="Sample size is not enough for an automatic decision.",
            )
        ],
    )


def _make_ic_series() -> list[FactorIcPoint]:
    return [
        FactorIcPoint(
            trade_date=date(2026, 3, 13),
            sample_size=3,
            ic=0.1,
            rank_ic=0.2,
        )
    ]


def _make_group_returns() -> list[FactorGroupReturnPoint]:
    return [
        FactorGroupReturnPoint(
            trade_date=date(2026, 3, 13),
            group_index=1,
            group_count=5,
            sample_size=10,
            average_forward_return=0.01,
        )
    ]


if __name__ == "__main__":
    unittest.main()
