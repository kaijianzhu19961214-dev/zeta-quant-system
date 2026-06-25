from datetime import datetime, timezone
import unittest

from fastapi.testclient import TestClient

from quant_ops_api.api.v1.dependencies import get_artifact_ledger_service
from quant_ops_api.main import create_app
from quant_ops_api.schemas import ArtifactLedgerItem, ArtifactLedgerResponse, TaskLedgerItem


class FakeArtifactLedgerService:
    def get_ledger(self) -> ArtifactLedgerResponse:
        return ArtifactLedgerResponse(
            generated_at=datetime.now(timezone.utc),
            source="test",
            persistence_status="not_persisted",
            task_count=1,
            artifact_count=1,
            tasks=[
                TaskLedgerItem(
                    task_id="task_1",
                    task_type="factor_validation",
                    task_name="momentum_1d_v1_1d",
                    owner="tester",
                    status="succeeded",
                    artifact_count=1,
                )
            ],
            artifacts=[
                ArtifactLedgerItem(
                    artifact_id="artifact_1",
                    task_id="task_1",
                    artifact_type="validation_report",
                    storage_type="preview_manifest",
                    object_key="factor_validation/momentum_1d/task_1/report.json",
                )
            ],
        )


class ArtifactLedgerRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.dependency_overrides[get_artifact_ledger_service] = lambda: FakeArtifactLedgerService()
        self.client = TestClient(self.app)

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    def test_should_return_artifact_ledger(self) -> None:
        response = self.client.get("/api/v1/artifacts/ledger")
        payload = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["task_count"], 1)
        self.assertEqual(payload["artifact_count"], 1)
        self.assertEqual(payload["tasks"][0]["task_type"], "factor_validation")
        self.assertEqual(payload["artifacts"][0]["artifact_type"], "validation_report")


if __name__ == "__main__":
    unittest.main()
