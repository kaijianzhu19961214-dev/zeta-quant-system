import unittest

from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class FactorValidationReviewServiceTest(unittest.TestCase):
    def test_should_return_mvp_review_surface(self) -> None:
        service = FactorValidationReviewService()

        response = service.get_review()

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.latest_metric.factor_name, "momentum_1d")
        self.assertEqual(response.latest_metric.decision, "review_required")
        self.assertEqual(response.manifest.task_type, "factor_validation")
        self.assertEqual(response.manifest.artifact_count, 3)
        self.assertEqual(response.manifest.artifacts[0].artifact_type, "validation_report")
        self.assertTrue(response.limitations)


if __name__ == "__main__":
    unittest.main()
