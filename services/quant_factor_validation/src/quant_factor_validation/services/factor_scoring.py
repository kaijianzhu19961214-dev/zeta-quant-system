from quant_contracts import (
    EvaluationEngine,
    FactorComparisonReport,
    FactorEvaluationResult,
    FactorScoreCard,
    FactorScoreComponent,
    FactorValidationMetric,
    FactorValidationReport,
)


def build_factor_score_card(
    *,
    metrics: FactorValidationMetric,
    report: FactorValidationReport,
) -> FactorScoreCard:
    score_components = [
        _build_ic_ir_score(metrics=metrics),
        _build_ic_mean_score(metrics=metrics),
        _build_rank_ic_score(metrics=metrics),
        _build_group_return_score(metrics=metrics),
        _build_coverage_score(metrics=metrics),
        _build_missing_penalty(metrics=metrics),
        _build_unmeasured_penalty(
            name="turnover_penalty",
            reason="Turnover is not measured in the current MVP validation run.",
        ),
        _build_unmeasured_penalty(
            name="drawdown_penalty",
            reason="Drawdown is not measured before the backtest stage.",
        ),
    ]
    final_score = _clamp_score(sum(component.score for component in score_components))

    return FactorScoreCard(
        factor_name=metrics.factor_name,
        evaluation_engine=metrics.evaluation_engine,
        final_score=final_score,
        review_decision=report.decision,
        score_components=score_components,
        warnings=_build_score_warnings(metrics=metrics),
    )


def build_factor_evaluation_result(
    *,
    metrics: FactorValidationMetric,
    report: FactorValidationReport,
    score_card: FactorScoreCard,
) -> FactorEvaluationResult:
    return FactorEvaluationResult(
        factor_name=metrics.factor_name,
        asset_class=metrics.asset_class,
        factor_mode=metrics.factor_mode,
        factor_family=metrics.factor_family,
        evaluation_engine=metrics.evaluation_engine,
        metrics=metrics,
        report=report,
        score_card=score_card,
    )


def build_factor_comparison_report(
    *,
    primary_result: FactorEvaluationResult,
    additional_results: list[FactorEvaluationResult] | None = None,
) -> FactorComparisonReport:
    engine_results = [primary_result, *(additional_results or [])]
    review_decisions = {
        result.report.decision
        for result in engine_results
        if result.report is not None
    }
    has_engine_disagreement = len(review_decisions) > 1

    return FactorComparisonReport(
        factor_name=primary_result.factor_name,
        primary_engine=primary_result.evaluation_engine,
        engine_results=engine_results,
        engine_count=len(engine_results),
        has_engine_disagreement=has_engine_disagreement,
        comparison_summary=_build_comparison_summary(
            primary_engine=primary_result.evaluation_engine,
            engine_count=len(engine_results),
            has_engine_disagreement=has_engine_disagreement,
        ),
    )


def _build_ic_ir_score(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.ic_ir is None:
        return FactorScoreComponent(
            name="ic_ir_score",
            raw_value=None,
            score=0.0,
            max_score=30.0,
            reason="ICIR is unavailable.",
        )

    score = min(abs(metrics.ic_ir) / 1.0 * 30.0, 30.0)
    return FactorScoreComponent(
        name="ic_ir_score",
        raw_value=metrics.ic_ir,
        score=score,
        max_score=30.0,
        reason="Scores absolute ICIR stability with a first-stage cap of 30.",
    )


def _build_rank_ic_score(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.rank_ic_mean is None:
        return FactorScoreComponent(
            name="rank_ic_score",
            raw_value=None,
            score=0.0,
            max_score=25.0,
            reason="Rank IC mean is unavailable.",
        )

    score = min(abs(metrics.rank_ic_mean) / 0.10 * 25.0, 25.0)
    return FactorScoreComponent(
        name="rank_ic_score",
        raw_value=metrics.rank_ic_mean,
        score=score,
        max_score=25.0,
        reason="Scores absolute Rank IC mean with a first-stage cap of 25.",
    )


def _build_ic_mean_score(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.ic_mean is None:
        return FactorScoreComponent(
            name="ic_mean_score",
            raw_value=None,
            score=0.0,
            max_score=10.0,
            reason="IC mean is unavailable.",
        )

    score = min(abs(metrics.ic_mean) / 0.05 * 10.0, 10.0)
    return FactorScoreComponent(
        name="ic_mean_score",
        raw_value=metrics.ic_mean,
        score=score,
        max_score=10.0,
        reason="Scores absolute IC mean with a first-stage cap of 10.",
    )


def _build_group_return_score(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.group_return_spread_mean is None:
        return FactorScoreComponent(
            name="group_return_score",
            raw_value=None,
            score=0.0,
            max_score=20.0,
            reason="Group return spread is unavailable.",
        )

    score = min(abs(metrics.group_return_spread_mean) / 0.05 * 20.0, 20.0)
    return FactorScoreComponent(
        name="group_return_score",
        raw_value=metrics.group_return_spread_mean,
        score=score,
        max_score=20.0,
        reason="Scores high-minus-low group return spread with a first-stage cap of 20.",
    )


def _build_coverage_score(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.coverage_ratio is None:
        return FactorScoreComponent(
            name="coverage_score",
            raw_value=None,
            score=0.0,
            max_score=15.0,
            reason="Coverage ratio is unavailable.",
        )

    score = min(max(metrics.coverage_ratio, 0.0) * 15.0, 15.0)
    return FactorScoreComponent(
        name="coverage_score",
        raw_value=metrics.coverage_ratio,
        score=score,
        max_score=15.0,
        reason="Scores effective sample coverage with a first-stage cap of 15.",
    )


def _build_missing_penalty(*, metrics: FactorValidationMetric) -> FactorScoreComponent:
    if metrics.missing_ratio is None:
        return FactorScoreComponent(
            name="missing_penalty",
            raw_value=None,
            score=0.0,
            max_score=10.0,
            reason="Missing ratio is unavailable.",
        )

    score = -min(max(metrics.missing_ratio, 0.0) / 0.50 * 10.0, 10.0)
    return FactorScoreComponent(
        name="missing_penalty",
        raw_value=metrics.missing_ratio,
        score=score,
        max_score=10.0,
        reason="Penalizes missing factor values with a first-stage floor of -10.",
    )


def _build_unmeasured_penalty(*, name: str, reason: str) -> FactorScoreComponent:
    return FactorScoreComponent(
        name=name,
        raw_value=None,
        score=0.0,
        max_score=0.0,
        reason=reason,
    )


def _build_score_warnings(*, metrics: FactorValidationMetric) -> list[str]:
    warnings: list[str] = []
    if metrics.effective_sample_count < 30:
        warnings.append("Effective sample count is below the first-stage review threshold.")
    if metrics.coverage_ratio is not None and metrics.coverage_ratio < 0.8:
        warnings.append("Coverage ratio is below the first-stage review threshold.")
    warnings.append("Turnover and drawdown penalties are placeholders until backtest metrics are available.")
    return warnings


def _build_comparison_summary(
    *,
    primary_engine: EvaluationEngine,
    engine_count: int,
    has_engine_disagreement: bool,
) -> str:
    if engine_count == 1:
        return f"Only {primary_engine.value} has produced a standardized evaluation result."
    if has_engine_disagreement:
        return "Evaluation engines disagree and require manual review."
    return "Evaluation engines agree on the current review decision."


def _clamp_score(value: float) -> float:
    return round(min(max(value, 0.0), 100.0), 6)
