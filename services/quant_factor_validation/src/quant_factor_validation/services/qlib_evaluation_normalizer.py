from datetime import date

from pydantic import Field, field_validator, model_validator

from quant_contracts import (
    AssetClass,
    EvaluationEngine,
    ExternalFactorValidationSummary,
    FactorEvaluationResult,
    FactorFamily,
    FactorMode,
    PriceMode,
)
from quant_contracts.schemas.common import ContractModel
from quant_factor_validation.services.external_evaluation_adapter import (
    build_external_factor_evaluation_result,
)
from quant_factor_validation.services.metric_payload_utils import (
    ExternalMetricValue,
    find_optional_float,
    find_optional_int,
    find_optional_ratio,
    normalize_factor_name,
    normalize_metric_values,
    normalize_optional_text,
    normalize_text_list,
)


class QlibMetricPayload(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    metric_values: dict[str, ExternalMetricValue] = Field(default_factory=dict)
    group_count: int = Field(default=5, ge=2, le=20)
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.MODEL
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    recorder_id: str | None = Field(default=None, max_length=128)
    experiment_name: str | None = Field(default=None, max_length=128)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("factor_name")
    @classmethod
    def validate_factor_name(cls, value: str) -> str:
        return normalize_factor_name(value=value)

    @field_validator(
        "universe_name",
        "validation_version",
        "run_id",
        "dataset_code",
        "batch_id",
        "source_version",
        "source_run_id",
        "recorder_id",
        "experiment_name",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value=value)

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return normalize_text_list(value=value)

    @field_validator("metric_values")
    @classmethod
    def normalize_metric_values(
        cls,
        value: dict[str, ExternalMetricValue],
    ) -> dict[str, ExternalMetricValue]:
        return normalize_metric_values(value=value)

    @model_validator(mode="after")
    def validate_metric_payload(self) -> "QlibMetricPayload":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


class QlibMetricSummary(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    mean_information_coefficient: float | None = Field(default=None, ge=-1.0, le=1.0)
    mean_rank_information_coefficient: float | None = Field(default=None, ge=-1.0, le=1.0)
    information_coefficient_std: float | None = Field(default=None, ge=0.0)
    information_coefficient_ir: float | None = None
    mean_long_short_return_spread: float | None = None
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    missing_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    group_count: int = Field(default=5, ge=2, le=20)
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.MODEL
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    recorder_id: str | None = Field(default=None, max_length=128)
    experiment_name: str | None = Field(default=None, max_length=128)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("factor_name")
    @classmethod
    def validate_factor_name(cls, value: str) -> str:
        return normalize_factor_name(value=value)

    @field_validator(
        "universe_name",
        "validation_version",
        "run_id",
        "dataset_code",
        "batch_id",
        "source_version",
        "source_run_id",
        "recorder_id",
        "experiment_name",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value=value)

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return normalize_text_list(value=value)

    @model_validator(mode="after")
    def validate_metric_summary(self) -> "QlibMetricSummary":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


def build_qlib_metric_summary_from_payload(
    *,
    payload: QlibMetricPayload,
) -> QlibMetricSummary:
    return QlibMetricSummary(
        factor_name=payload.factor_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        forward_days=payload.forward_days,
        sample_count=payload.sample_count,
        effective_sample_count=payload.effective_sample_count,
        mean_information_coefficient=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_MEAN_IC_ALIASES,
        ),
        mean_rank_information_coefficient=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_MEAN_RANK_IC_ALIASES,
        ),
        information_coefficient_std=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_IC_STD_ALIASES,
        ),
        information_coefficient_ir=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_IC_IR_ALIASES,
        ),
        mean_long_short_return_spread=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_LONG_SHORT_SPREAD_ALIASES,
        ),
        coverage_ratio=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_COVERAGE_RATIO_ALIASES,
        ),
        missing_ratio=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_MISSING_RATIO_ALIASES,
        ),
        group_count=find_optional_int(
            metric_values=payload.metric_values,
            aliases=_GROUP_COUNT_ALIASES,
        )
        or payload.group_count,
        asset_class=payload.asset_class,
        factor_mode=payload.factor_mode,
        factor_family=payload.factor_family,
        universe_name=payload.universe_name,
        price_mode=payload.price_mode,
        dataset_code=payload.dataset_code,
        batch_id=payload.batch_id,
        validation_version=payload.validation_version,
        run_id=payload.run_id,
        source_version=payload.source_version,
        source_run_id=payload.source_run_id or payload.recorder_id,
        recorder_id=payload.recorder_id,
        experiment_name=payload.experiment_name,
        warnings=payload.warnings,
        notes=payload.notes,
    )


def run_qlib_payload_evaluation(
    *,
    payload: QlibMetricPayload,
) -> FactorEvaluationResult:
    metrics = build_qlib_metric_summary_from_payload(payload=payload)
    return build_qlib_factor_evaluation_result(metrics=metrics)


def build_qlib_external_summary(
    *,
    metrics: QlibMetricSummary,
) -> ExternalFactorValidationSummary:
    coverage_ratio = _resolve_coverage_ratio(metrics=metrics)
    missing_ratio = _resolve_missing_ratio(metrics=metrics, coverage_ratio=coverage_ratio)

    return ExternalFactorValidationSummary(
        factor_name=metrics.factor_name,
        asset_class=metrics.asset_class,
        factor_mode=metrics.factor_mode,
        factor_family=metrics.factor_family,
        evaluation_engine=EvaluationEngine.QLIB,
        start_date=metrics.start_date,
        end_date=metrics.end_date,
        forward_days=metrics.forward_days,
        sample_count=metrics.sample_count,
        effective_sample_count=metrics.effective_sample_count,
        coverage_ratio=coverage_ratio,
        missing_ratio=missing_ratio,
        ic_mean=metrics.mean_information_coefficient,
        rank_ic_mean=metrics.mean_rank_information_coefficient,
        ic_std=metrics.information_coefficient_std,
        ic_ir=metrics.information_coefficient_ir,
        group_count=metrics.group_count,
        group_return_spread_mean=metrics.mean_long_short_return_spread,
        universe_name=metrics.universe_name,
        price_mode=metrics.price_mode,
        dataset_code=metrics.dataset_code,
        batch_id=metrics.batch_id,
        validation_version=metrics.validation_version,
        run_id=metrics.run_id,
        source_library="qlib",
        source_version=metrics.source_version,
        source_run_id=metrics.source_run_id,
        source_metric_names=_build_source_metric_names(metrics=metrics),
        warnings=metrics.warnings,
        notes=_build_summary_notes(metrics=metrics),
    )


def build_qlib_factor_evaluation_result(
    *,
    metrics: QlibMetricSummary,
) -> FactorEvaluationResult:
    summary = build_qlib_external_summary(metrics=metrics)
    return build_external_factor_evaluation_result(summary=summary)


def _resolve_coverage_ratio(*, metrics: QlibMetricSummary) -> float | None:
    if metrics.coverage_ratio is not None:
        return metrics.coverage_ratio
    if metrics.sample_count == 0:
        return None
    return round(metrics.effective_sample_count / metrics.sample_count, 6)


def _resolve_missing_ratio(
    *,
    metrics: QlibMetricSummary,
    coverage_ratio: float | None,
) -> float | None:
    if metrics.missing_ratio is not None:
        return metrics.missing_ratio
    if coverage_ratio is None:
        return None
    return round(max(1.0 - coverage_ratio, 0.0), 6)


def _build_source_metric_names(*, metrics: QlibMetricSummary) -> list[str]:
    source_metric_names: list[str] = []
    if metrics.mean_information_coefficient is not None:
        source_metric_names.append("qlib_ic")
    if metrics.mean_rank_information_coefficient is not None:
        source_metric_names.append("qlib_rank_ic")
    if metrics.information_coefficient_std is not None:
        source_metric_names.append("qlib_ic_std")
    if metrics.information_coefficient_ir is not None:
        source_metric_names.append("qlib_icir")
    if metrics.mean_long_short_return_spread is not None:
        source_metric_names.append("qlib_long_short_return")
    return source_metric_names


def _build_summary_notes(*, metrics: QlibMetricSummary) -> list[str]:
    notes = [*metrics.notes]
    if metrics.recorder_id:
        notes.append(f"qlib_recorder_id={metrics.recorder_id}")
    if metrics.experiment_name:
        notes.append(f"qlib_experiment_name={metrics.experiment_name}")
    return notes


_MEAN_IC_ALIASES = (
    "ic",
    "IC",
    "mean_ic",
    "ic_mean",
    "information_coefficient",
    "mean_information_coefficient",
)
_MEAN_RANK_IC_ALIASES = (
    "rank_ic",
    "Rank IC",
    "mean_rank_ic",
    "rank_ic_mean",
    "rank_information_coefficient",
    "mean_rank_information_coefficient",
)
_IC_STD_ALIASES = (
    "ic_std",
    "IC Std.",
    "ic_standard_deviation",
    "information_coefficient_std",
)
_IC_IR_ALIASES = (
    "icir",
    "ICIR",
    "ic_ir",
    "IC IR",
    "information_coefficient_ir",
    "risk_adjusted_ic",
)
_LONG_SHORT_SPREAD_ALIASES = (
    "long_short_return",
    "long_short_mean_return",
    "long_short_spread",
    "mean_long_short_return",
    "mean_long_short_return_spread",
    "return_spread",
    "group_return_spread_mean",
)
_COVERAGE_RATIO_ALIASES = (
    "coverage_ratio",
    "coverage",
    "prediction_coverage",
    "label_coverage",
)
_MISSING_RATIO_ALIASES = (
    "missing_ratio",
    "missing",
    "prediction_missing_ratio",
    "label_missing_ratio",
)
_GROUP_COUNT_ALIASES = (
    "group_count",
    "quantile_count",
    "quantiles",
)
