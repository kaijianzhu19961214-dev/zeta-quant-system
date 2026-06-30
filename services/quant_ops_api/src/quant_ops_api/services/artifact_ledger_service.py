from datetime import datetime, timezone

from quant_ops_api.schemas import (
    ArtifactLedgerItem,
    ArtifactLedgerResponse,
    FactorValidationReviewResponse,
    TaskLedgerItem,
)
from quant_ops_api.services.factor_validation_review_service import FactorValidationReviewService


class ArtifactLedgerService:
    def __init__(self, *, validation_review_service: FactorValidationReviewService) -> None:
        self.validation_review_service = validation_review_service

    def get_ledger(self) -> ArtifactLedgerResponse:
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
