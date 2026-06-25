from datetime import datetime, timezone

from quant_ops_api.schemas import (
    FactorValidationArtifactSummary,
    FactorValidationFindingSummary,
    FactorValidationManifestSummary,
    FactorValidationMetricSummary,
    FactorValidationReviewResponse,
)


class FactorValidationReviewService:
    def get_review(self) -> FactorValidationReviewResponse:
        generated_at = datetime.now(timezone.utc)
        latest_metric = _build_latest_metric()
        artifacts = _build_artifacts(run_id=latest_metric.run_id)

        return FactorValidationReviewResponse(
            generated_at=generated_at,
            source="quant_factor_validation_mvp_preview",
            persistence_status="not_persisted",
            latest_metric=latest_metric,
            findings=[
                FactorValidationFindingSummary(
                    severity="info",
                    code="manual_review_required",
                    message="Sample size, coverage, or IC stability is not enough for an automatic candidate decision.",
                )
            ],
            recommended_actions=[
                "Expand the validation sample and add factor decay plus quantile-return checks.",
                "Persist manifest and report outputs before using this view as an audit ledger.",
            ],
            manifest=FactorValidationManifestSummary(
                manifest_id=f"manifest_{latest_metric.run_id}",
                task_id=latest_metric.run_id,
                task_name=f"{latest_metric.factor_name}_{latest_metric.validation_version}_{latest_metric.forward_days}d",
                task_type="factor_validation",
                persistence_status="not_persisted",
                artifact_count=len(artifacts),
                artifacts=artifacts,
            ),
            limitations=[
                "当前摘要来自 MVP manifest preview，不代表已写入 PostgreSQL 或 MinIO。",
                "生产报告列表应后续接入 task_runs、task_artifacts 或 MinIO latest.json。",
            ],
        )


def _build_latest_metric() -> FactorValidationMetricSummary:
    return FactorValidationMetricSummary(
        factor_name="momentum_1d",
        validation_version="v1",
        run_id="run_validation_preview",
        forward_days=1,
        sample_count=2,
        effective_sample_count=2,
        coverage_ratio=1.0,
        missing_ratio=0.0,
        ic_mean=1.0,
        rank_ic_mean=1.0,
        ic_ir=None,
        group_count=2,
        group_return_spread_mean=0.1,
        decision="review_required",
    )


def _build_artifacts(*, run_id: str) -> list[FactorValidationArtifactSummary]:
    object_prefix = f"factor_validation/momentum_1d/{run_id}"
    return [
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_validation_report",
            artifact_type="validation_report",
            object_key=f"{object_prefix}/validation_report.json",
            schema_version="factor_validation_report.v1",
            persistence_status="not_persisted",
        ),
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_metrics",
            artifact_type="metrics_table",
            object_key=f"{object_prefix}/metrics.json",
            schema_version="factor_validation_metrics.v1",
            persistence_status="not_persisted",
        ),
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_ic_series",
            artifact_type="metrics_table",
            object_key=f"{object_prefix}/ic_series.json",
            schema_version="factor_ic_series.v1",
            persistence_status="not_persisted",
        ),
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_group_returns",
            artifact_type="metrics_table",
            object_key=f"{object_prefix}/group_returns.json",
            schema_version="factor_group_returns.v1",
            persistence_status="not_persisted",
        ),
    ]
