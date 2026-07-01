from datetime import datetime, timezone

from quant_ops_api.schemas import (
    ExternalMetricPayload,
    ExternalPayloadComparisonRequest,
    FactorComparisonSummary,
    FactorScoreCardSummary,
    FactorScoreComponentSummary,
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
            score_card=_build_score_card(),
            comparison=FactorComparisonSummary(
                primary_engine="internal",
                engine_count=1,
                has_engine_disagreement=False,
                comparison_summary="Only internal has produced a standardized evaluation result.",
            ),
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

    def get_external_payload_comparison_preview_request(self) -> ExternalPayloadComparisonRequest:
        return ExternalPayloadComparisonRequest(
            factor_name="momentum_20d",
            primary_engine="alphalens",
            alphalens_payloads=[
                ExternalMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=180,
                    effective_sample_count=170,
                    metric_values={
                        "mean_ic": 0.035,
                        "rank_ic_mean": 0.06,
                        "ic_std": 0.08,
                        "ic_ir": 0.4375,
                        "mean_return_spread": 0.045,
                    },
                    source_version="0.4.0",
                    source_run_id="alphalens_payload_preview",
                )
            ],
            qlib_payloads=[
                ExternalMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=180,
                    effective_sample_count=166,
                    metric_values={
                        "ic_mean": 0.033,
                        "rank_ic_mean": 0.055,
                        "ic_std": 0.08,
                        "icir": 0.4125,
                        "return_spread": 0.04,
                    },
                    recorder_id="qlib_recorder_preview",
                    experiment_name="alpha158_lgbm",
                )
            ],
            vectorbt_payloads=[
                ExternalMetricPayload(
                    factor_name="momentum_20d",
                    start_date="2026-01-01",
                    end_date="2026-03-13",
                    forward_days=5,
                    sample_count=120,
                    effective_sample_count=110,
                    metric_values={
                        "annualized_return": 0.22,
                        "sharpe": 1.1,
                        "max_dd": -0.08,
                        "turnover_ratio": 0.4,
                    },
                    portfolio_name="momentum_20d_portfolio",
                    parameter_set_id="lookback_20_hold_5",
                )
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
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_score_card",
            artifact_type="metrics_table",
            object_key=f"{object_prefix}/score_card.json",
            schema_version="factor_score_card.v1",
            persistence_status="not_persisted",
        ),
        FactorValidationArtifactSummary(
            artifact_id=f"{run_id}_comparison_report",
            artifact_type="metrics_table",
            object_key=f"{object_prefix}/comparison_report.json",
            schema_version="factor_comparison_report.v1",
            persistence_status="not_persisted",
        ),
    ]


def _build_score_card() -> FactorScoreCardSummary:
    return FactorScoreCardSummary(
        factor_name="momentum_1d",
        evaluation_engine="internal",
        final_score=64.0,
        review_decision="review_required",
        score_components=[
            FactorScoreComponentSummary(
                name="ic_mean_score",
                raw_value=1.0,
                score=10.0,
                max_score=10.0,
                reason="Scores absolute IC mean with a first-stage cap of 10.",
            ),
            FactorScoreComponentSummary(
                name="rank_ic_score",
                raw_value=1.0,
                score=25.0,
                max_score=25.0,
                reason="Scores absolute Rank IC mean with a first-stage cap of 25.",
            ),
            FactorScoreComponentSummary(
                name="group_return_score",
                raw_value=0.1,
                score=20.0,
                max_score=20.0,
                reason="Scores high-minus-low group return spread with a first-stage cap of 20.",
            ),
            FactorScoreComponentSummary(
                name="coverage_score",
                raw_value=1.0,
                score=15.0,
                max_score=15.0,
                reason="Scores effective sample coverage with a first-stage cap of 15.",
            ),
            FactorScoreComponentSummary(
                name="turnover_penalty",
                raw_value=None,
                score=0.0,
                max_score=0.0,
                reason="Turnover is not measured in the current MVP validation run.",
            ),
        ],
        warnings=["Turnover and drawdown penalties are placeholders until backtest metrics are available."],
    )
