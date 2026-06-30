from datetime import datetime, timezone

from quant_contracts import (
    ArtifactType,
    FactorComparisonReport,
    FactorGroupReturnPoint,
    FactorIcPoint,
    FactorScoreCard,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationReport,
    FactorValidationRequest,
    TaskArtifact,
    TaskRun,
    TaskStatus,
)


def build_validation_manifest(
    *,
    request: FactorValidationRequest,
    metrics: FactorValidationMetric,
    report: FactorValidationReport,
    ic_series: list[FactorIcPoint],
    group_returns: list[FactorGroupReturnPoint],
    score_card: FactorScoreCard | None = None,
    comparison_report: FactorComparisonReport | None = None,
) -> FactorValidationManifest:
    run_id = _resolve_run_id(request=request, metrics=metrics)
    safe_factor_name = _safe_path_part(metrics.factor_name)
    safe_run_id = _safe_path_part(run_id)
    object_prefix = f"factor_validation/{safe_factor_name}/{safe_run_id}"

    task_run = TaskRun(
        task_id=run_id,
        task_type="factor_validation",
        task_name=f"{metrics.factor_name}_{metrics.validation_version}_{metrics.forward_days}d",
        status=TaskStatus.SUCCEEDED,
        input_params={
            "factor_name": metrics.factor_name,
            "universe_name": metrics.universe_name,
            "timeframe": request.timeframe,
            "price_mode": metrics.price_mode,
            "dataset_code": metrics.dataset_code,
            "batch_id": metrics.batch_id,
            "validation_version": metrics.validation_version,
            "forward_days": metrics.forward_days,
            "market_start": str(request.market_start),
            "market_end": str(request.market_end),
            "sample_count": metrics.sample_count,
        },
        output_summary={
            "effective_sample_count": metrics.effective_sample_count,
            "coverage_ratio": metrics.coverage_ratio,
            "missing_ratio": metrics.missing_ratio,
            "ic_mean": metrics.ic_mean,
            "rank_ic_mean": metrics.rank_ic_mean,
            "ic_ir": metrics.ic_ir,
            "group_count": metrics.group_count,
            "group_return_spread_mean": metrics.group_return_spread_mean,
            "decision": report.decision,
        },
        finished_at=datetime.now(timezone.utc),
    )

    artifacts = [
        _build_report_artifact(
            run_id=run_id,
            object_prefix=object_prefix,
            report=report,
        ),
        _build_metrics_artifact(
            run_id=run_id,
            object_prefix=object_prefix,
            metrics=metrics,
        ),
        _build_ic_series_artifact(
            run_id=run_id,
            object_prefix=object_prefix,
            ic_series=ic_series,
        ),
        _build_group_returns_artifact(
            run_id=run_id,
            object_prefix=object_prefix,
            group_returns=group_returns,
        ),
    ]
    if score_card is not None:
        artifacts.append(
            _build_score_card_artifact(
                run_id=run_id,
                object_prefix=object_prefix,
                score_card=score_card,
            )
        )
    if comparison_report is not None:
        artifacts.append(
            _build_comparison_report_artifact(
                run_id=run_id,
                object_prefix=object_prefix,
                comparison_report=comparison_report,
            )
        )

    return FactorValidationManifest(
        manifest_id=f"manifest_{safe_run_id}",
        task_run=task_run,
        artifacts=artifacts,
        persistence_status="not_persisted",
        created_at=datetime.now(timezone.utc),
    )


def _build_report_artifact(
    *,
    run_id: str,
    object_prefix: str,
    report: FactorValidationReport,
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_validation_report",
        task_id=run_id,
        artifact_type=ArtifactType.VALIDATION_REPORT,
        object_key=f"{object_prefix}/validation_report.json",
        metadata={
            "decision": report.decision,
            "finding_count": len(report.findings),
            "schema_version": "factor_validation_report.v1",
            "persistence_status": "not_persisted",
        },
    )


def _build_metrics_artifact(
    *,
    run_id: str,
    object_prefix: str,
    metrics: FactorValidationMetric,
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_metrics",
        task_id=run_id,
        artifact_type=ArtifactType.METRICS_TABLE,
        object_key=f"{object_prefix}/metrics.json",
        metadata={
            "factor_name": metrics.factor_name,
            "effective_sample_count": metrics.effective_sample_count,
            "ic_mean": metrics.ic_mean,
            "rank_ic_mean": metrics.rank_ic_mean,
            "schema_version": "factor_validation_metrics.v1",
            "persistence_status": "not_persisted",
        },
    )


def _build_ic_series_artifact(
    *,
    run_id: str,
    object_prefix: str,
    ic_series: list[FactorIcPoint],
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_ic_series",
        task_id=run_id,
        artifact_type=ArtifactType.METRICS_TABLE,
        object_key=f"{object_prefix}/ic_series.json",
        metadata={
            "row_count": len(ic_series),
            "schema_version": "factor_ic_series.v1",
            "persistence_status": "not_persisted",
        },
    )


def _build_group_returns_artifact(
    *,
    run_id: str,
    object_prefix: str,
    group_returns: list[FactorGroupReturnPoint],
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_group_returns",
        task_id=run_id,
        artifact_type=ArtifactType.METRICS_TABLE,
        object_key=f"{object_prefix}/group_returns.json",
        metadata={
            "row_count": len(group_returns),
            "schema_version": "factor_group_returns.v1",
            "persistence_status": "not_persisted",
        },
    )


def _build_score_card_artifact(
    *,
    run_id: str,
    object_prefix: str,
    score_card: FactorScoreCard,
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_score_card",
        task_id=run_id,
        artifact_type=ArtifactType.METRICS_TABLE,
        object_key=f"{object_prefix}/score_card.json",
        metadata={
            "factor_name": score_card.factor_name,
            "evaluation_engine": score_card.evaluation_engine,
            "final_score": score_card.final_score,
            "review_decision": score_card.review_decision,
            "schema_version": "factor_score_card.v1",
            "persistence_status": "not_persisted",
        },
    )


def _build_comparison_report_artifact(
    *,
    run_id: str,
    object_prefix: str,
    comparison_report: FactorComparisonReport,
) -> TaskArtifact:
    return TaskArtifact(
        artifact_id=f"{_safe_path_part(run_id)}_comparison_report",
        task_id=run_id,
        artifact_type=ArtifactType.METRICS_TABLE,
        object_key=f"{object_prefix}/comparison_report.json",
        metadata={
            "factor_name": comparison_report.factor_name,
            "primary_engine": comparison_report.primary_engine,
            "engine_count": comparison_report.engine_count,
            "has_engine_disagreement": comparison_report.has_engine_disagreement,
            "schema_version": "factor_comparison_report.v1",
            "persistence_status": "not_persisted",
        },
    )


def _resolve_run_id(*, request: FactorValidationRequest, metrics: FactorValidationMetric) -> str:
    if request.run_id:
        return request.run_id
    return (
        f"validation_{metrics.factor_name}_{metrics.start_date.isoformat()}_"
        f"{metrics.end_date.isoformat()}_{metrics.forward_days}d"
    )


def _safe_path_part(value: str) -> str:
    normalized_value = "".join(
        character if character.isalnum() or character in {"_", "-", "."} else "_"
        for character in value.strip()
    )
    if normalized_value:
        return normalized_value
    return "unknown"
