from datetime import UTC, datetime
import hashlib
from typing import Protocol

from quant_contracts import (
    AlgorithmReviewGate,
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceRecord,
    AlgorithmReviewGateEvidenceResponse,
    AlgorithmReviewGateEvidenceSubmission,
    AlgorithmSpec,
)

from quant_factor_lab.algorithms import FactorAlgorithmRegistry, create_default_algorithm_registry


class AlgorithmReviewServiceError(Exception):
    def __init__(self, *, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class AlgorithmReviewEvidenceRepository(Protocol):
    async def record_evidence(
        self,
        *,
        record: AlgorithmReviewGateEvidenceRecord,
    ) -> AlgorithmReviewGateEvidenceRecord:
        raise NotImplementedError

    async def list_evidence(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> list[AlgorithmReviewGateEvidenceRecord]:
        raise NotImplementedError


class AlgorithmReviewService:
    def __init__(
        self,
        *,
        algorithm_registry: FactorAlgorithmRegistry | None = None,
        evidence_repository: AlgorithmReviewEvidenceRepository | None = None,
    ) -> None:
        self.algorithm_registry = algorithm_registry or create_default_algorithm_registry()
        self.evidence_repository = evidence_repository

    def preview_evidence_record(
        self,
        *,
        submission: AlgorithmReviewGateEvidenceSubmission,
        submitted_at: datetime | None = None,
    ) -> AlgorithmReviewGateEvidenceResponse:
        record = self._build_evidence_record(submission=submission, submitted_at=submitted_at)
        return AlgorithmReviewGateEvidenceResponse(
            record=record,
            limitations=[
                "MVP only validates and previews the evidence record; it does not persist it.",
                "Gate status remains unchanged until a reviewed evidence record is persisted and audited.",
            ],
        )

    async def submit_evidence_record(
        self,
        *,
        submission: AlgorithmReviewGateEvidenceSubmission,
        submitted_at: datetime | None = None,
    ) -> AlgorithmReviewGateEvidenceResponse:
        if self.evidence_repository is None:
            raise AlgorithmReviewServiceError(
                status_code=503,
                message="algorithm review evidence repository is not configured",
            )

        record = self._build_evidence_record(submission=submission, submitted_at=submitted_at)
        try:
            persisted_record = await self.evidence_repository.record_evidence(record=record)
        except Exception as error:
            raise AlgorithmReviewServiceError(
                status_code=502,
                message="failed to persist algorithm review evidence",
            ) from error
        return AlgorithmReviewGateEvidenceResponse(
            record=persisted_record,
            persistence_status="persisted",
            limitations=[
                "Gate status remains unchanged until an explicit review decision is recorded.",
            ],
        )

    async def list_evidence_records(
        self,
        *,
        algorithm_id: str,
        gate_id: str | None = None,
        limit: int = 50,
    ) -> AlgorithmReviewGateEvidenceListResponse:
        algorithm_spec = self._get_algorithm_spec(algorithm_id=algorithm_id)
        if gate_id is not None:
            self._get_review_gate(algorithm_spec=algorithm_spec, gate_id=gate_id)

        if self.evidence_repository is None:
            return AlgorithmReviewGateEvidenceListResponse(
                algorithm_id=algorithm_spec.algorithm_id,
                gate_id=gate_id,
                records=[],
                total_count=0,
                limitations=[
                    "Algorithm review evidence repository is not configured.",
                ],
            )

        try:
            records = await self.evidence_repository.list_evidence(
                algorithm_id=algorithm_spec.algorithm_id,
                gate_id=gate_id,
                limit=limit,
            )
        except Exception as error:
            raise AlgorithmReviewServiceError(
                status_code=502,
                message="failed to list algorithm review evidence",
            ) from error
        return AlgorithmReviewGateEvidenceListResponse(
            algorithm_id=algorithm_spec.algorithm_id,
            gate_id=gate_id,
            records=records,
            total_count=len(records),
            persistence_status="persisted",
        )

    def _build_evidence_record(
        self,
        *,
        submission: AlgorithmReviewGateEvidenceSubmission,
        submitted_at: datetime | None = None,
    ) -> AlgorithmReviewGateEvidenceRecord:
        algorithm_spec = self._get_algorithm_spec(algorithm_id=submission.algorithm_id)
        review_gate = self._get_review_gate(algorithm_spec=algorithm_spec, gate_id=submission.gate_id)
        effective_submitted_at = submitted_at or datetime.now(tz=UTC)

        return AlgorithmReviewGateEvidenceRecord(
            evidence_id=_build_evidence_id(submission=submission, submitted_at=effective_submitted_at),
            algorithm_id=algorithm_spec.algorithm_id,
            gate_id=review_gate.gate_id,
            gate_category=review_gate.category,
            gate_title=review_gate.title,
            previous_gate_status=review_gate.status,
            submitted_by=submission.submitted_by,
            evidence_type=submission.evidence_type,
            evidence_source=submission.evidence_source,
            summary=submission.summary,
            artifact_id=submission.artifact_id,
            artifact_uri=submission.artifact_uri,
            source_url=submission.source_url,
            notes=submission.notes,
            submitted_at=effective_submitted_at,
            is_required=review_gate.is_required,
        )

    def _get_algorithm_spec(self, *, algorithm_id: str) -> AlgorithmSpec:
        for spec in self.algorithm_registry.list_specs(include_planned=True):
            if spec.algorithm_id == algorithm_id:
                return spec
        raise AlgorithmReviewServiceError(status_code=404, message=f"algorithm not found: {algorithm_id}")

    def _get_review_gate(self, *, algorithm_spec: AlgorithmSpec, gate_id: str) -> AlgorithmReviewGate:
        for gate in algorithm_spec.review_gates:
            if gate.gate_id == gate_id:
                return gate
        raise AlgorithmReviewServiceError(
            status_code=404,
            message=f"review gate not found: {algorithm_spec.algorithm_id}/{gate_id}",
        )


def _build_evidence_id(
    *,
    submission: AlgorithmReviewGateEvidenceSubmission,
    submitted_at: datetime,
) -> str:
    raw_value = ":".join(
        [
            submission.algorithm_id,
            submission.gate_id,
            submission.submitted_by,
            submission.evidence_source,
            submitted_at.isoformat(),
        ]
    )
    digest = hashlib.sha256(raw_value.encode("utf-8")).hexdigest()[:16]
    return f"algorithm_gate_evidence_{digest}"
