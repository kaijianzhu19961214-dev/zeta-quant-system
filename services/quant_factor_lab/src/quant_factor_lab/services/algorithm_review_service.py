from datetime import UTC, datetime
import hashlib
from typing import Protocol

from quant_contracts import (
    AlgorithmGatePromotionFinding,
    AlgorithmPromotionReadinessResponse,
    AlgorithmReviewGate,
    AlgorithmReviewGateEvidenceListResponse,
    AlgorithmReviewGateEvidenceRecord,
    AlgorithmReviewGateEvidenceReviewRequest,
    AlgorithmReviewGateEvidenceResponse,
    AlgorithmReviewGateEvidenceSubmission,
    AlgorithmSpec,
)

from quant_factor_lab.algorithms import FactorAlgorithmRegistry, create_default_algorithm_registry
from quant_factor_lab.repositories.algorithm_review_evidence import AlgorithmReviewEvidenceNotFoundError


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

    async def review_evidence(
        self,
        *,
        evidence_id: str,
        evidence_status: str,
        reviewed_by: str,
        reviewed_at: datetime,
        review_comment: str | None = None,
    ) -> AlgorithmReviewGateEvidenceRecord:
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

    async def review_evidence_record(
        self,
        *,
        evidence_id: str,
        request: AlgorithmReviewGateEvidenceReviewRequest,
        reviewed_at: datetime | None = None,
    ) -> AlgorithmReviewGateEvidenceResponse:
        if self.evidence_repository is None:
            raise AlgorithmReviewServiceError(
                status_code=503,
                message="algorithm review evidence repository is not configured",
            )

        effective_reviewed_at = reviewed_at or datetime.now(tz=UTC)
        try:
            record = await self.evidence_repository.review_evidence(
                evidence_id=evidence_id,
                evidence_status=request.evidence_status,
                reviewed_by=request.reviewed_by,
                reviewed_at=effective_reviewed_at,
                review_comment=request.review_comment,
            )
        except AlgorithmReviewEvidenceNotFoundError as error:
            raise AlgorithmReviewServiceError(
                status_code=404,
                message=f"algorithm review evidence not found: {evidence_id}",
            ) from error
        except Exception as error:
            raise AlgorithmReviewServiceError(
                status_code=502,
                message="failed to review algorithm review evidence",
            ) from error

        return AlgorithmReviewGateEvidenceResponse(
            record=record,
            persistence_status="persisted",
            limitations=[
                "Review decision updates the evidence record; gate status promotion is evaluated separately.",
            ],
        )

    async def evaluate_promotion_readiness(
        self,
        *,
        algorithm_id: str,
        limit: int = 200,
        generated_at: datetime | None = None,
    ) -> AlgorithmPromotionReadinessResponse:
        algorithm_spec = self._get_algorithm_spec(algorithm_id=algorithm_id)
        records: list[AlgorithmReviewGateEvidenceRecord] = []
        limitations: list[str] = [
            "Promotion readiness is a read-only evaluation; it does not mutate AlgorithmSpec.status.",
        ]

        if self.evidence_repository is None:
            limitations.append("Algorithm review evidence repository is not configured.")
        else:
            try:
                records = await self.evidence_repository.list_evidence(
                    algorithm_id=algorithm_spec.algorithm_id,
                    limit=limit,
                )
            except Exception as error:
                raise AlgorithmReviewServiceError(
                    status_code=502,
                    message="failed to list algorithm review evidence for promotion readiness",
                ) from error

        findings = [
            _build_gate_promotion_finding(
                gate=gate,
                records=[record for record in records if record.gate_id == gate.gate_id],
            )
            for gate in algorithm_spec.review_gates
        ]
        required_findings = [finding for finding in findings if finding.is_required]
        unmet_required_findings = [finding for finding in required_findings if not finding.is_met]
        rejected_required_gate_ids = [
            finding.gate_id
            for finding in unmet_required_findings
            if finding.decision == "blocked_rejected_evidence"
        ]
        missing_required_gate_ids = [
            finding.gate_id
            for finding in unmet_required_findings
            if finding.decision != "blocked_rejected_evidence"
        ]
        can_promote = len(unmet_required_findings) == 0

        return AlgorithmPromotionReadinessResponse(
            algorithm_id=algorithm_spec.algorithm_id,
            current_status=algorithm_spec.status,
            decision="promotable" if can_promote else "blocked",
            can_promote=can_promote,
            required_gate_count=len(required_findings),
            met_required_gate_count=len(required_findings) - len(unmet_required_findings),
            missing_required_gate_ids=missing_required_gate_ids,
            rejected_required_gate_ids=rejected_required_gate_ids,
            findings=findings,
            generated_at=generated_at or datetime.now(tz=UTC),
            limitations=limitations,
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


def _build_gate_promotion_finding(
    *,
    gate: AlgorithmReviewGate,
    records: list[AlgorithmReviewGateEvidenceRecord],
) -> AlgorithmGatePromotionFinding:
    accepted_evidence_count = sum(1 for record in records if record.evidence_status == "accepted")
    latest_record = _select_latest_evidence_record(records=records)
    latest_evidence_status = latest_record.evidence_status if latest_record is not None else None

    if not gate.is_required or gate.status == "not_applicable":
        return AlgorithmGatePromotionFinding(
            gate_id=gate.gate_id,
            gate_title=gate.title,
            gate_status=gate.status,
            decision="not_applicable",
            is_required=gate.is_required,
            is_met=True,
            accepted_evidence_count=accepted_evidence_count,
            latest_evidence_status=latest_evidence_status,
            message="Gate is not required for promotion readiness.",
        )

    if gate.status == "satisfied":
        return AlgorithmGatePromotionFinding(
            gate_id=gate.gate_id,
            gate_title=gate.title,
            gate_status=gate.status,
            decision="met_by_registry",
            is_required=True,
            is_met=True,
            accepted_evidence_count=accepted_evidence_count,
            latest_evidence_status=latest_evidence_status,
            message="Registry review gate is already marked satisfied.",
        )

    if latest_evidence_status == "rejected" and accepted_evidence_count == 0:
        return AlgorithmGatePromotionFinding(
            gate_id=gate.gate_id,
            gate_title=gate.title,
            gate_status=gate.status,
            decision="blocked_rejected_evidence",
            is_required=True,
            is_met=False,
            accepted_evidence_count=accepted_evidence_count,
            latest_evidence_status=latest_evidence_status,
            message="Latest reviewed evidence was rejected and no accepted evidence is available.",
        )

    if accepted_evidence_count > 0:
        return AlgorithmGatePromotionFinding(
            gate_id=gate.gate_id,
            gate_title=gate.title,
            gate_status=gate.status,
            decision="met_by_accepted_evidence",
            is_required=True,
            is_met=True,
            accepted_evidence_count=accepted_evidence_count,
            latest_evidence_status=latest_evidence_status,
            message="Accepted evidence satisfies the missing required gate.",
        )

    return AlgorithmGatePromotionFinding(
        gate_id=gate.gate_id,
        gate_title=gate.title,
        gate_status=gate.status,
        decision="blocked_missing_evidence",
        is_required=True,
        is_met=False,
        accepted_evidence_count=accepted_evidence_count,
        latest_evidence_status=latest_evidence_status,
        message="Required gate is missing accepted evidence.",
    )


def _select_latest_evidence_record(
    *,
    records: list[AlgorithmReviewGateEvidenceRecord],
) -> AlgorithmReviewGateEvidenceRecord | None:
    if not records:
        return None

    return max(records, key=lambda record: record.reviewed_at or record.submitted_at)
