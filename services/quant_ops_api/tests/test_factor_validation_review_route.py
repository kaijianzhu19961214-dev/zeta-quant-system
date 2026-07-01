from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient
from quant_contracts import FactorComparisonReport

from quant_ops_api.api.v1.dependencies import (
    get_artifact_ledger_service,
    get_factor_validation_client,
    get_factor_validation_review_service,
)
from quant_ops_api.clients import FactorValidationClientError
from quant_ops_api.main import create_app
from quant_ops_api.schemas import (
    ExternalMetricPayload,
    ExternalPayloadComparisonRequest,
    FactorComparisonArtifactReference,
    FactorValidationArtifactSummary,
    FactorValidationManifestSummary,
    FactorValidationMetricSummary,
    FactorValidationReviewResponse,
)


class FakeFactorValidationReviewService:
    def get_review(self) -> FactorValidationReviewResponse:
        metric = FactorValidationMetricSummary(
            factor_name="momentum_1d",
            validation_version="v1",
            run_id="run_test",
            forward_days=1,
            sample_count=10,
            effective_sample_count=8,
            decision="review_required",
        )

        return FactorValidationReviewResponse(
            generated_at=datetime.now(timezone.utc),
            source="test",
            persistence_status="not_persisted",
            latest_metric=metric,
            manifest=FactorValidationManifestSummary(
                manifest_id="manifest_run_test",
                task_id="run_test",
                task_name="momentum_1d_v1_1d",
                task_type="factor_validation",
                persistence_status="not_persisted",
                artifact_count=1,
                artifacts=[
                    FactorValidationArtifactSummary(
                        artifact_id="run_test_validation_report",
                        artifact_type="validation_report",
                        object_key="factor_validation/momentum_1d/run_test/validation_report.json",
                        schema_version="factor_validation_report.v1",
                        persistence_status="not_persisted",
                    )
                ],
            ),
        )

    def get_external_payload_comparison_preview_request(self) -> ExternalPayloadComparisonRequest:
        return ExternalPayloadComparisonRequest(
            factor_name="momentum_20d",
            primary_engine="alphalens",
            alphalens_payloads=[
                ExternalMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=180,
                    effective_sample_count=170,
                    metric_values={"mean_ic": 0.035},
                )
            ],
        )


class FakeFactorValidationClient:
    async def compare_external_payloads(self, *, request):
        return FactorComparisonReport(
            factor_name=request.factor_name,
            primary_engine=request.primary_engine,
            engine_count=2,
            has_engine_disagreement=False,
            comparison_summary="Evaluation engines agree on the current review decision.",
        )


class RejectingFactorValidationClient:
    async def compare_external_payloads(self, *, request):
        raise FactorValidationClientError(
            status_code=422,
            message="primary_engine must have at least one matching payload",
        )


class FakeArtifactLedgerService:
    async def find_latest_factor_comparison_artifact(self) -> FactorComparisonArtifactReference:
        return FactorComparisonArtifactReference(
            artifact_id="validation_run_1_comparison_report",
            task_id="validation_run_1",
            storage_type="minio_s3",
            bucket_name="quant-factor-data",
            object_key="factor_validation/momentum_20d/validation_run_1/comparison_report.json",
            uri="s3://quant-factor-data/factor_validation/momentum_20d/validation_run_1/comparison_report.json",
            file_size_bytes=2048,
            schema_version="factor_comparison_report.v1",
            created_at=datetime.now(timezone.utc),
        )


class FactorValidationReviewRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_factor_validation_review_service] = (
            lambda: FakeFactorValidationReviewService()
        )
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_return_factor_validation_review(self) -> None:
        response = self.client.get("/api/v1/factor-validation/review")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["persistence_status"], "not_persisted")
        self.assertEqual(payload["latest_metric"]["decision"], "review_required")
        self.assertEqual(payload["manifest"]["artifact_count"], 1)

    def test_should_proxy_external_payload_comparison(self) -> None:
        self.app.dependency_overrides[get_factor_validation_client] = lambda: FakeFactorValidationClient()

        response = self.client.post(
            "/api/v1/factor-validation/external-payloads/compare",
            json={
                "factor_name": "momentum_20d",
                "primary_engine": "alphalens",
                "alphalens_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 180,
                        "effective_sample_count": 170,
                        "metric_values": {"mean_ic": 0.035},
                    }
                ],
                "qlib_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 180,
                        "effective_sample_count": 166,
                        "metric_values": {"ic_mean": 0.033},
                    }
                ],
            },
        )

        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["factor_name"], "momentum_20d")
        self.assertEqual(payload["primary_engine"], "alphalens")
        self.assertEqual(payload["engine_count"], 2)

    def test_should_return_external_payload_comparison_preview(self) -> None:
        self.app.dependency_overrides[get_factor_validation_client] = lambda: FakeFactorValidationClient()
        self.app.dependency_overrides[get_artifact_ledger_service] = lambda: FakeArtifactLedgerService()

        response = self.client.get("/api/v1/factor-validation/external-payloads/preview")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["source"], "postgres_factor_comparison_artifact_reference")
        self.assertTrue(payload["limitations"])
        self.assertEqual(payload["artifact_reference"]["storage_type"], "minio_s3")
        self.assertEqual(payload["artifact_reference"]["schema_version"], "factor_comparison_report.v1")
        self.assertEqual(payload["comparison_report"]["factor_name"], "momentum_20d")
        self.assertEqual(payload["comparison_report"]["primary_engine"], "alphalens")
        self.assertEqual(payload["comparison_report"]["engine_count"], 2)

    def test_should_keep_validation_error_from_external_payload_comparison(self) -> None:
        self.app.dependency_overrides[get_factor_validation_client] = lambda: RejectingFactorValidationClient()

        response = self.client.post(
            "/api/v1/factor-validation/external-payloads/compare",
            json={
                "factor_name": "momentum_20d",
                "primary_engine": "vectorbt",
                "alphalens_payloads": [
                    {
                        "factor_name": "momentum_20d",
                        "start_date": "2026-01-01",
                        "end_date": "2026-03-13",
                        "forward_days": 5,
                        "sample_count": 10,
                        "effective_sample_count": 8,
                    }
                ],
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "primary_engine must have at least one matching payload")


if __name__ == "__main__":
    unittest.main()
