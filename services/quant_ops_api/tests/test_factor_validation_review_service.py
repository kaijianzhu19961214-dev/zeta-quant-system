import unittest

from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class FactorValidationReviewServiceTest(unittest.TestCase):
    def test_should_return_mvp_review_surface(self) -> None:
        service = FactorValidationReviewService()

        response = service.get_review()

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.latest_metric.factor_name, "momentum_1d")
        self.assertEqual(response.latest_metric.decision, "review_required")
        self.assertEqual(response.latest_metric.group_count, 2)
        self.assertEqual(response.latest_metric.group_return_spread_mean, 0.1)
        self.assertIsNotNone(response.score_card)
        self.assertEqual(response.score_card.evaluation_engine, "internal")
        self.assertGreaterEqual(response.score_card.final_score, 0)
        self.assertIsNotNone(response.comparison)
        self.assertEqual(response.comparison.engine_count, 1)
        self.assertEqual(response.manifest.task_type, "factor_validation")
        self.assertEqual(response.manifest.artifact_count, 6)
        self.assertEqual(response.manifest.artifacts[0].artifact_type, "validation_report")
        self.assertEqual(response.manifest.artifacts[3].schema_version, "factor_group_returns.v1")
        self.assertEqual(response.manifest.artifacts[4].schema_version, "factor_score_card.v1")
        self.assertEqual(
            response.manifest.artifacts[5].schema_version,
            "factor_comparison_report.v1",
        )
        self.assertTrue(response.limitations)


if __name__ == "__main__":
    unittest.main()
