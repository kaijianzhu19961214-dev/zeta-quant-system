from datetime import datetime, timezone
import unittest

from quant_ops_api.repositories import ValidationLedgerSnapshot
from quant_ops_api.schemas import ArtifactLedgerItem, TaskLedgerItem
from quant_ops_api.services.artifact_ledger_service import ArtifactLedgerService
from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class FakeValidationLedgerReader:
    def __init__(self) -> None:
        self.latest_limit: int | None = None

    async def read_latest_snapshot(self, *, limit: int) -> ValidationLedgerSnapshot:
        self.latest_limit = limit
        generated_at = datetime.now(timezone.utc)
        return ValidationLedgerSnapshot(
            generated_at=generated_at,
            tasks=[
                TaskLedgerItem(
                    task_id="validation_run_1",
                    task_type="factor_validation",
                    task_name="momentum_1d_v1_1d",
                    owner="quant_factor_validation",
                    status="succeeded",
                    output_summary={"factor_score": 64.0},
                    finished_at=generated_at,
                    artifact_count=1,
                )
            ],
            artifacts=[
                ArtifactLedgerItem(
                    artifact_id="validation_run_1_score_card",
                    task_id="validation_run_1",
                    artifact_type="metrics_table",
                    storage_type="minio_s3",
                    bucket_name="quant-factor-data",
                    object_key="factor_validation/momentum_1d/validation_run_1/score_card.json",
                    schema_version="factor_score_card.v1",
                    metadata={"schema_version": "factor_score_card.v1"},
                    created_at=generated_at,
                )
            ],
        )


class ArtifactLedgerServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_return_preview_ledger_from_validation_review(self) -> None:
        service = ArtifactLedgerService(validation_review_service=FactorValidationReviewService())

        response = await service.get_ledger()

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.task_count, 1)
        self.assertEqual(response.artifact_count, 6)
        self.assertEqual(response.tasks[0].task_type, "factor_validation")
        self.assertEqual(response.tasks[0].status, "succeeded")
        self.assertEqual(response.tasks[0].output_summary["evaluation_engine"], "internal")
        self.assertGreaterEqual(response.tasks[0].output_summary["factor_score"], 0)
        self.assertEqual(response.artifacts[0].storage_type, "preview_manifest")
        self.assertEqual(response.artifacts[3].schema_version, "factor_group_returns.v1")
        self.assertEqual(response.artifacts[4].schema_version, "factor_score_card.v1")
        self.assertEqual(response.artifacts[5].schema_version, "factor_comparison_report.v1")
        self.assertIn("source_manifest_id", response.artifacts[0].metadata)

    async def test_should_return_persisted_ledger_from_reader_when_configured(self) -> None:
        reader = FakeValidationLedgerReader()
        service = ArtifactLedgerService(
            validation_review_service=FactorValidationReviewService(),
            validation_ledger_reader=reader,
            query_limit=12,
        )

        response = await service.get_ledger()

        self.assertEqual(response.persistence_status, "persisted")
        self.assertEqual(response.source, "postgres_validation_ledger")
        self.assertEqual(response.task_count, 1)
        self.assertEqual(response.artifact_count, 1)
        self.assertEqual(response.tasks[0].task_id, "validation_run_1")
        self.assertEqual(response.artifacts[0].schema_version, "factor_score_card.v1")
        self.assertEqual(reader.latest_limit, 12)


if __name__ == "__main__":
    unittest.main()
