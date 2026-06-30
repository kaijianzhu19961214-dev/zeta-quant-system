from quant_contracts import (
    ExternalFactorValidationSummary,
    FactorEvaluationResult,
    FactorValidationFinding,
    FactorValidationMetric,
    FactorValidationReport,
)
from quant_factor_validation.services.factor_scoring import (
    build_factor_evaluation_result,
    build_factor_score_card,
)
from quant_factor_validation.services.validation_report import build_validation_report


def build_external_factor_validation_metric(
    *,
    summary: ExternalFactorValidationSummary,
) -> FactorValidationMetric:
    return FactorValidationMetric(
        factor_name=summary.factor_name,
        asset_class=summary.asset_class,
        factor_mode=summary.factor_mode,
        factor_family=summary.factor_family,
        evaluation_engine=summary.evaluation_engine,
        start_date=summary.start_date,
        end_date=summary.end_date,
        forward_days=summary.forward_days,
        sample_count=summary.sample_count,
        effective_sample_count=summary.effective_sample_count,
        coverage_ratio=summary.coverage_ratio,
        missing_ratio=summary.missing_ratio,
        ic_mean=summary.ic_mean,
        rank_ic_mean=summary.rank_ic_mean,
        ic_std=summary.ic_std,
        ic_ir=summary.ic_ir,
        group_count=summary.group_count,
        group_return_spread_mean=summary.group_return_spread_mean,
        universe_name=summary.universe_name,
        price_mode=summary.price_mode,
        dataset_code=summary.dataset_code,
        batch_id=summary.batch_id,
        validation_version=summary.validation_version,
        run_id=summary.run_id or summary.source_run_id,
    )


def build_external_factor_evaluation_result(
    *,
    summary: ExternalFactorValidationSummary,
) -> FactorEvaluationResult:
    metrics = build_external_factor_validation_metric(summary=summary)
    report = _build_external_validation_report(summary=summary, metrics=metrics)
    score_card = build_factor_score_card(metrics=metrics, report=report)

    return build_factor_evaluation_result(
        metrics=metrics,
        report=report,
        score_card=score_card,
    )


def _build_external_validation_report(
    *,
    summary: ExternalFactorValidationSummary,
    metrics: FactorValidationMetric,
) -> FactorValidationReport:
    base_report = build_validation_report(metrics=metrics)
    findings = [
        *base_report.findings,
        _build_adapter_finding(summary=summary),
        *_build_warning_findings(warnings=summary.warnings),
    ]
    recommended_actions = [
        *base_report.recommended_actions,
        "Compare the external engine result with internal validation before production approval.",
    ]

    if not summary.source_metric_names:
        findings.append(
            FactorValidationFinding(
                severity="info",
                code="external_metric_mapping_missing",
                message="External source metric names were not supplied for audit traceability.",
            )
        )

    return FactorValidationReport(
        decision=base_report.decision,
        summary=base_report.summary,
        findings=findings,
        recommended_actions=recommended_actions,
    )


def _build_adapter_finding(*, summary: ExternalFactorValidationSummary) -> FactorValidationFinding:
    source_label = summary.source_library
    if summary.source_version:
        source_label = f"{summary.source_library} {summary.source_version}"

    return FactorValidationFinding(
        severity="info",
        code="external_engine_adapter",
        message=(
            f"{summary.evaluation_engine.value} result from {source_label} "
            "was mapped into the standard factor evaluation contract."
        ),
    )


def _build_warning_findings(*, warnings: list[str]) -> list[FactorValidationFinding]:
    return [
        FactorValidationFinding(
            severity="warning",
            code=f"external_engine_warning_{index}",
            message=_truncate_finding_message(warning),
        )
        for index, warning in enumerate(warnings[:5], start=1)
    ]


def _truncate_finding_message(value: str) -> str:
    if len(value) <= 256:
        return value
    return f"{value[:253]}..."
