from datetime import datetime, timezone
from typing import Protocol

from quant_ops_api.repositories import ValidationLedgerSnapshot
from quant_ops_api.schemas import (
    ArtifactLedgerItem,
    ArtifactLedgerResponse,
    FactorComparisonArtifactReference,
    FactorValidationReviewResponse,
    TaskLedgerItem,
)
from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class ValidationLedgerReader(Protocol):
    async def read_latest_snapshot(self, *, limit: int) -> ValidationLedgerSnapshot:
        raise NotImplementedError


COMPARISON_REPORT_SCHEMA_VERSION = "factor_comparison_report.v1"


class ArtifactLedgerService:
    def __init__(
        self,
        *,
        validation_review_service: FactorValidationReviewService,
        validation_ledger_reader: ValidationLedgerReader | None = None,
        query_limit: int = 20,
    ) -> None:
        self.validation_review_service = validation_review_service
        self.validation_ledger_reader = validation_ledger_reader
        self.query_limit = query_limit

    async def get_ledger(self) -> ArtifactLedgerResponse:
        if self.validation_ledger_reader is not None:
            snapshot = await self.validation_ledger_reader.read_latest_snapshot(limit=self.query_limit)
            return _build_persisted_ledger(snapshot=snapshot)

        return self._build_preview_ledger()

    async def find_latest_factor_comparison_artifact(self) -> FactorComparisonArtifactReference | None:
        if self.validation_ledger_reader is not None:
            snapshot = await self.validation_ledger_reader.read_latest_snapshot(limit=self.query_limit)
            return _find_comparison_reference(artifacts=snapshot.artifacts)

        preview_ledger = self._build_preview_ledger()
        return _find_comparison_reference(artifacts=preview_ledger.artifacts)

    def _build_preview_ledger(self) -> ArtifactLedgerResponse:
        generated_at = datetime.now(timezone.utc)
        validation_review = self.validation_review_service.get_review()
        tasks = [_build_validation_task(validation_review=validation_review)]
        artifacts = _build_validation_artifacts(validation_review=validation_review)

        return ArtifactLedgerResponse(
            generated_at=generated_at,
            source="ops_api_preview_ledger",
            persistence_status="not_persisted",
            task_count=len(tasks),
            artifact_count=len(artifacts),
            tasks=tasks,
            artifacts=artifacts,
            limitations=[
                "当前账本由本地 preview 派生，不代表已读取 101 PostgreSQL task_runs / task_artifacts。",
                "接入生产账本时应使用只读数据库用户或只读 API，并继续隐藏 MinIO 管理密钥。",
            ],
        )


def _build_persisted_ledger(*, snapshot: ValidationLedgerSnapshot) -> ArtifactLedgerResponse:
    return ArtifactLedgerResponse(
        generated_at=snapshot.generated_at,
        source="postgres_validation_ledger",
        persistence_status="persisted",
        task_count=len(snapshot.tasks),
        artifact_count=len(snapshot.artifacts),
        tasks=snapshot.tasks,
        artifacts=snapshot.artifacts,
        limitations=[
            "当前账本来自 PostgreSQL task_runs / task_artifacts 只读查询。",
            "Web UI 仍不能持有数据库写权限或 MinIO 管理密钥。",
        ],
    )


def _build_validation_task(*, validation_review: FactorValidationReviewResponse) -> TaskLedgerItem:
    metric = validation_review.latest_metric
    manifest = validation_review.manifest
    score_card = validation_review.score_card

    return TaskLedgerItem(
        task_id=manifest.task_id,
        task_type=manifest.task_type,
        task_name=manifest.task_name,
        owner="quant_factor_validation",
        status="succeeded",
        input_params={
            "factor_name": metric.factor_name,
            "validation_version": metric.validation_version,
            "forward_days": metric.forward_days,
        },
        output_summary={
            "decision": metric.decision,
            "effective_sample_count": metric.effective_sample_count,
            "coverage_ratio": metric.coverage_ratio,
            "ic_mean": metric.ic_mean,
            "rank_ic_mean": metric.rank_ic_mean,
            "group_count": metric.group_count,
            "group_return_spread_mean": metric.group_return_spread_mean,
            "factor_score": score_card.final_score if score_card is not None else None,
            "evaluation_engine": score_card.evaluation_engine if score_card is not None else None,
            "artifact_count": manifest.artifact_count,
        },
        finished_at=validation_review.generated_at,
        artifact_count=manifest.artifact_count,
    )


def _build_validation_artifacts(
    *,
    validation_review: FactorValidationReviewResponse,
) -> list[ArtifactLedgerItem]:
    manifest = validation_review.manifest
    return [
        ArtifactLedgerItem(
            artifact_id=artifact.artifact_id,
            task_id=manifest.task_id,
            artifact_type=artifact.artifact_type,
            storage_type="preview_manifest",
            object_key=artifact.object_key,
            schema_version=artifact.schema_version,
            metadata={
                "persistence_status": artifact.persistence_status,
                "source_manifest_id": manifest.manifest_id,
            },
            created_at=validation_review.generated_at,
        )
        for artifact in manifest.artifacts
    ]


def _find_comparison_reference(
    *,
    artifacts: list[ArtifactLedgerItem],
) -> FactorComparisonArtifactReference | None:
    for artifact in artifacts:
        if artifact.schema_version == COMPARISON_REPORT_SCHEMA_VERSION:
            return _build_comparison_artifact_reference(artifact=artifact)
    return None


def _build_comparison_artifact_reference(
    *,
    artifact: ArtifactLedgerItem,
) -> FactorComparisonArtifactReference:
    return FactorComparisonArtifactReference(
        artifact_id=artifact.artifact_id,
        task_id=artifact.task_id,
        storage_type=artifact.storage_type,
        bucket_name=artifact.bucket_name,
        object_key=artifact.object_key,
        uri=artifact.uri,
        file_size_bytes=artifact.file_size_bytes,
        schema_version=artifact.schema_version,
        created_at=artifact.created_at,
    )
