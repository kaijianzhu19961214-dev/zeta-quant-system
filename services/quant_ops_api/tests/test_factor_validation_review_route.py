from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from quant_ops_api.api.v1.dependencies import get_factor_validation_review_service
from quant_ops_api.main import create_app
from quant_ops_api.schemas import (
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


if __name__ == "__main__":
    unittest.main()
