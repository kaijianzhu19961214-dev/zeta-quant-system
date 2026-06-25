import unittest

from quant_ops_api.services.artifact_ledger_service import ArtifactLedgerService
from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class ArtifactLedgerServiceTest(unittest.TestCase):
    def test_should_return_preview_ledger_from_validation_review(self) -> None:
        service = ArtifactLedgerService(validation_review_service=FactorValidationReviewService())

        response = service.get_ledger()

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.task_count, 1)
        self.assertEqual(response.artifact_count, 3)
        self.assertEqual(response.tasks[0].task_type, "factor_validation")
        self.assertEqual(response.tasks[0].status, "succeeded")
        self.assertEqual(response.artifacts[0].storage_type, "preview_manifest")
        self.assertIn("source_manifest_id", response.artifacts[0].metadata)


if __name__ == "__main__":
    unittest.main()
