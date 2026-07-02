import unittest
from datetime import UTC, datetime

from quant_contracts import (
    AlgorithmReviewGateEvidenceRecord,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceSubmission,
)

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

    def test_should_preview_momentum_validation_evidence_when_gate_exists(self) -> None:
        service = AlgorithmReviewService()
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            submitted_by="codex_smoke",
            evidence_type="validation_report",
            evidence_source="factor_validation/momentum_1d/real_flow_smoke_101/comparison_report.json",
            summary="Momentum validation smoke evidence from 101 data.",
            artifact_id="comparison_report_momentum_1d",
        )

        response = service.preview_evidence_record(submission=submission)

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.record.algorithm_id, "technical.momentum")
        self.assertEqual(response.record.gate_id, "validation_evidence")
        self.assertEqual(response.record.gate_category, "validation")
        self.assertEqual(response.record.previous_gate_status, "satisfied")

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


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.records: list[AlgorithmReviewGateEvidenceRecord] = []

    async def record_evidence(
        self,
        *,
        record: AlgorithmReviewGateEvidenceRecord,
    ) -> AlgorithmReviewGateEvidenceRecord:
        self.records.append(record)
        return record

    async def list_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> list[AlgorithmReviewGateEvidenceRecord]:
        records = [record for record in self.records if record.algorithm_id == algorithm_id]
        if gate_id is not None:
            records = [record for record in records if record.gate_id == gate_id]
        return records[:limit]

    async def review_evidence(
        self,
        *,
        evidence_id: str,
        evidence_status: str,
        reviewed_by: str,
        reviewed_at: datetime,
        review_comment: str | None = None,
    ) -> AlgorithmReviewGateEvidenceRecord:
        for index, record in enumerate(self.records):
            if record.evidence_id != evidence_id:
                continue

            updated_record = record.model_copy(
                update={
                    "evidence_status": evidence_status,
                    "reviewed_by": reviewed_by,
                    "reviewed_at": reviewed_at,
                    "review_comment": review_comment,
                }
            )
            self.records[index] = updated_record
            return updated_record

        raise RuntimeError("not found")


class AlgorithmReviewServicePersistenceTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_submit_evidence_record_when_repository_is_configured(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            submitted_by="codex_smoke",
            evidence_type="validation_report",
            evidence_source="factor_validation/momentum_1d/comparison_report.json",
            summary="Momentum validation smoke evidence from 101 data.",
        )

        response = await service.submit_evidence_record(submission=submission)

        self.assertEqual(response.persistence_status, "persisted")
        self.assertEqual(response.record.algorithm_id, "technical.momentum")
        self.assertEqual(response.record.gate_id, "validation_evidence")
        self.assertEqual(repository.records[0].evidence_id, response.record.evidence_id)

    async def test_should_list_evidence_records_when_repository_is_configured(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            submitted_by="codex_smoke",
            evidence_type="validation_report",
            evidence_source="factor_validation/momentum_1d/comparison_report.json",
            summary="Momentum validation smoke evidence from 101 data.",
        )
        await service.submit_evidence_record(submission=submission)

        response = await service.list_evidence_records(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
        )

        self.assertEqual(response.persistence_status, "persisted")
        self.assertEqual(response.total_count, 1)
        self.assertEqual(response.records[0].gate_id, "validation_evidence")

    async def test_should_return_empty_list_when_repository_is_not_configured(self) -> None:
        service = AlgorithmReviewService()

        response = await service.list_evidence_records(algorithm_id="technical.momentum")

        self.assertEqual(response.persistence_status, "not_persisted")
        self.assertEqual(response.total_count, 0)
        self.assertIn("not configured", response.limitations[0])

    async def test_should_raise_unavailable_when_submit_repository_is_not_configured(self) -> None:
        service = AlgorithmReviewService()
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            submitted_by="codex_smoke",
            evidence_type="validation_report",
            evidence_source="factor_validation/momentum_1d/comparison_report.json",
            summary="Momentum validation smoke evidence from 101 data.",
        )

        with self.assertRaises(AlgorithmReviewServiceError) as context:
            await service.submit_evidence_record(submission=submission)

        self.assertEqual(context.exception.status_code, 503)

    async def test_should_review_evidence_record_when_repository_is_configured(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="technical.momentum",
            gate_id="validation_evidence",
            submitted_by="codex_smoke",
            evidence_type="validation_report",
            evidence_source="factor_validation/momentum_1d/comparison_report.json",
            summary="Momentum validation smoke evidence from 101 data.",
        )
        submitted_response = await service.submit_evidence_record(submission=submission)
        review_request = AlgorithmReviewGateEvidenceReviewRequest(
            reviewed_by="researcher_lead",
            evidence_status="accepted",
            review_comment="Evidence accepted.",
        )

        reviewed_response = await service.review_evidence_record(
            evidence_id=submitted_response.record.evidence_id,
            request=review_request,
        )

        self.assertEqual(reviewed_response.persistence_status, "persisted")
        self.assertEqual(reviewed_response.record.evidence_status, "accepted")
        self.assertEqual(reviewed_response.record.reviewed_by, "researcher_lead")
        self.assertEqual(reviewed_response.record.review_comment, "Evidence accepted.")

    async def test_should_mark_available_algorithm_promotable_when_required_gates_are_satisfied(self) -> None:
        service = AlgorithmReviewService()

        response = await service.evaluate_promotion_readiness(algorithm_id="technical.momentum")

        self.assertTrue(response.can_promote)
        self.assertEqual(response.decision, "promotable")
        self.assertEqual(response.current_status, "available")
        self.assertEqual(response.required_gate_count, 6)
        self.assertEqual(response.met_required_gate_count, 6)
        self.assertEqual(response.missing_required_gate_ids, [])
        self.assertEqual(response.rejected_required_gate_ids, [])
        self.assertTrue(all(finding.decision == "met_by_registry" for finding in response.findings))

    async def test_should_block_planned_algorithm_when_required_evidence_is_missing(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)

        response = await service.evaluate_promotion_readiness(algorithm_id="volatility.egarch")

        data_policy_finding = next(
            finding for finding in response.findings if finding.gate_id == "data_policy_fixed"
        )

        self.assertFalse(response.can_promote)
        self.assertEqual(response.decision, "blocked")
        self.assertEqual(response.current_status, "planned")
        self.assertEqual(response.required_gate_count, 6)
        self.assertEqual(response.met_required_gate_count, 1)
        self.assertIn("data_policy_fixed", response.missing_required_gate_ids)
        self.assertEqual(data_policy_finding.decision, "blocked_missing_evidence")

    async def test_should_count_accepted_evidence_for_missing_gate_when_reviewed(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="volatility.egarch",
            gate_id="data_policy_fixed",
            submitted_by="researcher_a",
            evidence_type="research_note",
            evidence_source="research_notes/egarch_data_policy.md",
            summary="Return input, adjustment mode, and minimum history policy are fixed.",
        )
        submitted_response = await service.submit_evidence_record(submission=submission)
        review_request = AlgorithmReviewGateEvidenceReviewRequest(
            reviewed_by="researcher_lead",
            evidence_status="accepted",
            review_comment="Data policy evidence accepted.",
        )
        await service.review_evidence_record(
            evidence_id=submitted_response.record.evidence_id,
            request=review_request,
        )

        response = await service.evaluate_promotion_readiness(algorithm_id="volatility.egarch")
        data_policy_finding = next(
            finding for finding in response.findings if finding.gate_id == "data_policy_fixed"
        )

        self.assertFalse(response.can_promote)
        self.assertEqual(response.decision, "blocked")
        self.assertEqual(response.met_required_gate_count, 2)
        self.assertNotIn("data_policy_fixed", response.missing_required_gate_ids)
        self.assertIn("validation_evidence", response.missing_required_gate_ids)
        self.assertEqual(data_policy_finding.decision, "met_by_accepted_evidence")
        self.assertEqual(data_policy_finding.accepted_evidence_count, 1)
        self.assertEqual(data_policy_finding.latest_evidence_status, "accepted")

    async def test_should_report_rejected_required_gate_when_latest_evidence_is_rejected(self) -> None:
        repository = FakeEvidenceRepository()
        service = AlgorithmReviewService(evidence_repository=repository)
        submission = AlgorithmReviewGateEvidenceSubmission(
            algorithm_id="volatility.egarch",
            gate_id="validation_evidence",
            submitted_by="researcher_a",
            evidence_type="validation_report",
            evidence_source="factor_validation/egarch_20d/comparison_report.json",
            summary="Rank IC and turnover evidence for EGARCH candidate.",
        )
        submitted_response = await service.submit_evidence_record(submission=submission)
        review_request = AlgorithmReviewGateEvidenceReviewRequest(
            reviewed_by="researcher_lead",
            evidence_status="rejected",
            review_comment="Validation window is too short.",
        )
        await service.review_evidence_record(
            evidence_id=submitted_response.record.evidence_id,
            request=review_request,
        )

        response = await service.evaluate_promotion_readiness(algorithm_id="volatility.egarch")
        validation_finding = next(
            finding for finding in response.findings if finding.gate_id == "validation_evidence"
        )

        self.assertFalse(response.can_promote)
        self.assertIn("validation_evidence", response.rejected_required_gate_ids)
        self.assertNotIn("validation_evidence", response.missing_required_gate_ids)
        self.assertEqual(validation_finding.decision, "blocked_rejected_evidence")
        self.assertEqual(validation_finding.latest_evidence_status, "rejected")


if __name__ == "__main__":
    unittest.main()
