from quant_contracts import (
    FactorValidationFinding,
    FactorValidationMetric,
    FactorValidationReport,
)


MIN_CANDIDATE_COVERAGE_RATIO = 0.8
MIN_CANDIDATE_EFFECTIVE_SAMPLE_COUNT = 30
MIN_ABSOLUTE_IC_MEAN = 0.03
MIN_ABSOLUTE_IC_IR = 0.3
MIN_ABSOLUTE_RANK_IC_MEAN = 0.05
LOW_COVERAGE_RATIO = 0.6
HIGH_MISSING_RATIO = 0.2


def build_validation_report(*, metrics: FactorValidationMetric) -> FactorValidationReport:
    findings: list[FactorValidationFinding] = []
    recommended_actions: list[str] = []

    if metrics.effective_sample_count == 0:
        return FactorValidationReport(
            decision="insufficient_data",
            summary="No effective factor-return pairs were available for validation.",
            findings=[
                FactorValidationFinding(
                    severity="error",
                    code="no_effective_sample",
                    message="No factor values could be aligned with forward returns.",
                )
            ],
            recommended_actions=[
                "Check market_start, market_end, forward_days, symbols, and price_mode.",
                "Run validation on a wider sample before reviewing factor quality.",
            ],
        )

    if metrics.coverage_ratio is not None and metrics.coverage_ratio < LOW_COVERAGE_RATIO:
        findings.append(
            FactorValidationFinding(
                severity="warning",
                code="low_coverage",
                message="Effective validation coverage is below the review threshold.",
            )
        )
        recommended_actions.append("Review missing forward returns and symbol coverage.")

    if metrics.missing_ratio is not None and metrics.missing_ratio > HIGH_MISSING_RATIO:
        findings.append(
            FactorValidationFinding(
                severity="warning",
                code="high_missing_ratio",
                message="The submitted factor values contain a high missing-value ratio.",
            )
        )
        recommended_actions.append("Check factor construction, warm-up windows, and missing-value policy.")

    if metrics.ic_mean is None and metrics.rank_ic_mean is None:
        return FactorValidationReport(
            decision="insufficient_data",
            summary="IC metrics could not be computed from the effective sample.",
            findings=findings
            + [
                FactorValidationFinding(
                    severity="error",
                    code="missing_ic_metrics",
                    message="IC and Rank IC are both unavailable.",
                )
            ],
            recommended_actions=recommended_actions
            + ["Increase cross-sectional sample size for each trade date."],
        )

    has_candidate_sample = _has_candidate_sample(metrics=metrics)
    has_directional_signal = _has_directional_signal(metrics=metrics)
    has_stable_ic = metrics.ic_ir is not None and abs(metrics.ic_ir) >= MIN_ABSOLUTE_IC_IR

    if has_candidate_sample and has_directional_signal and has_stable_ic:
        return FactorValidationReport(
            decision="candidate_pass",
            summary="The factor has enough sample coverage and directional IC evidence for candidate review.",
            findings=findings,
            recommended_actions=recommended_actions
            + ["Add quantile return, turnover, cost, and robustness checks before production use."],
        )

    if has_candidate_sample and not has_directional_signal:
        return FactorValidationReport(
            decision="candidate_reject",
            summary="The factor has enough sample coverage but weak IC evidence in this validation run.",
            findings=findings
            + [
                FactorValidationFinding(
                    severity="warning",
                    code="weak_ic_signal",
                    message="Absolute IC and Rank IC means are below candidate thresholds.",
                )
            ],
            recommended_actions=recommended_actions
            + ["Review the factor hypothesis, horizon, universe, and preprocessing choices."],
        )

    return FactorValidationReport(
        decision="review_required",
        summary="The validation result needs manual review before candidate approval or rejection.",
        findings=findings
        + [
            FactorValidationFinding(
                severity="info",
                code="manual_review_required",
                message="Sample size, coverage, or IC stability is not enough for an automatic candidate decision.",
            )
        ],
        recommended_actions=recommended_actions
        + ["Expand the validation sample and add factor decay plus quantile-return checks."],
    )


def _has_candidate_sample(*, metrics: FactorValidationMetric) -> bool:
    if metrics.effective_sample_count < MIN_CANDIDATE_EFFECTIVE_SAMPLE_COUNT:
        return False
    if metrics.coverage_ratio is None:
        return False
    return metrics.coverage_ratio >= MIN_CANDIDATE_COVERAGE_RATIO


def _has_directional_signal(*, metrics: FactorValidationMetric) -> bool:
    if metrics.ic_mean is not None and abs(metrics.ic_mean) >= MIN_ABSOLUTE_IC_MEAN:
        return True
    if metrics.rank_ic_mean is not None and abs(metrics.rank_ic_mean) >= MIN_ABSOLUTE_RANK_IC_MEAN:
        return True
    return False
