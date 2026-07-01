import unittest
from datetime import UTC, datetime

from quant_contracts import AlgorithmReviewGateEvidenceSubmission

from quant_factor_lab.services.algorithm_review_service import AlgorithmReviewService, AlgorithmReviewServiceError


class AlgorithmReviewServiceTest(unittest.TestCase):
    def test_should_preview_evidence_record_when_gate_exists(self) -> None:
        service = AlgorithmReviewService()
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="volatility.egarch",
            gate_id="validation_evidence",
            submitted_by="researcher_a",
            evidence_type="validation_report",
            evidence_source="factor_validation/egarch_20d/comparison_report.json",
            summary="Rank IC, IC decay, and turnover evidence for EGARCH.",
            artifact_id="egarch_20d_comparison_report",
        )
        submitted_at = datetime(2026, 7, 1, 10, 0, tzinfo=UTC)

        response = service.preview_evidence_record(submission=submission, submitted_at=submitted_at)

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.record.algorithm_id, "volatility.egarch")
        self.assertEqual(response.record.gate_id, "validation_evidence")
        self.assertEqual(response.record.gate_category, "validation")
        self.assertEqual(response.record.previous_gate_status, "missing")
        self.assertEqual(response.record.evidence_status, "submitted")
        self.assertEqual(response.record.submitted_at, submitted_at)
        self.assertIn("does not persist", response.limitations[0])

    def test_should_raise_not_found_when_algorithm_does_not_exist(self) -> None:
        service = AlgorithmReviewService()
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="volatility.unknown",
            gate_id="validation_evidence",
            submitted_by="researcher_a",
            evidence_type="validation_report",
            evidence_source="factor_validation/unknown/report.json",
            summary="Validation evidence for an unknown algorithm.",
        )

        with self.assertRaises(AlgorithmReviewServiceError) as context:
            service.preview_evidence_record(submission=submission)

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("algorithm not found", context.exception.message)

    def test_should_raise_not_found_when_gate_does_not_exist(self) -> None:
        service = AlgorithmReviewService()
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="volatility.egarch",
            gate_id="unknown_gate",
            submitted_by="researcher_a",
            evidence_type="validation_report",
            evidence_source="factor_validation/egarch_20d/report.json",
            summary="Validation evidence for an unknown gate.",
        )

        with self.assertRaises(AlgorithmReviewServiceError) as context:
            service.preview_evidence_record(submission=submission)

        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("review gate not found", context.exception.message)


if __name__ == "__main__":
    unittest.main()
