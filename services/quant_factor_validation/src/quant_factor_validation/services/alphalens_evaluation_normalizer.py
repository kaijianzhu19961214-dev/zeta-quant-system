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


class AlphalensMetricSummary(ContractModel):
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
    mean_quantile_return_spread: float | None = None
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    missing_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    group_count: int = Field(default=5, ge=2, le=20)
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("factor_name")
    @classmethod
    def validate_factor_name(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("factor_name must use lowercase letters, numbers, and underscores")

    @field_validator(
        "universe_name",
        "validation_version",
        "run_id",
        "dataset_code",
        "batch_id",
        "source_version",
        "source_run_id",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_metric_summary(self) -> "AlphalensMetricSummary":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


def build_alphalens_external_summary(
    *,
    metrics: AlphalensMetricSummary,
) -> ExternalFactorValidationSummary:
    coverage_ratio = _resolve_coverage_ratio(metrics=metrics)
    missing_ratio = _resolve_missing_ratio(metrics=metrics, coverage_ratio=coverage_ratio)

    return ExternalFactorValidationSummary(
        factor_name=metrics.factor_name,
        asset_class=metrics.asset_class,
        factor_mode=metrics.factor_mode,
        factor_family=metrics.factor_family,
        evaluation_engine=EvaluationEngine.ALPHALENS,
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
        group_return_spread_mean=metrics.mean_quantile_return_spread,
        universe_name=metrics.universe_name,
        price_mode=metrics.price_mode,
        dataset_code=metrics.dataset_code,
        batch_id=metrics.batch_id,
        validation_version=metrics.validation_version,
        run_id=metrics.run_id,
        source_library="alphalens",
        source_version=metrics.source_version,
        source_run_id=metrics.source_run_id,
        source_metric_names=_build_source_metric_names(metrics=metrics),
        warnings=metrics.warnings,
        notes=metrics.notes,
    )


def build_alphalens_factor_evaluation_result(
    *,
    metrics: AlphalensMetricSummary,
) -> FactorEvaluationResult:
    summary = build_alphalens_external_summary(metrics=metrics)
    return build_external_factor_evaluation_result(summary=summary)


def _resolve_coverage_ratio(*, metrics: AlphalensMetricSummary) -> float | None:
    if metrics.coverage_ratio is not None:
        return metrics.coverage_ratio
    if metrics.sample_count == 0:
        return None
    return round(metrics.effective_sample_count / metrics.sample_count, 6)


def _resolve_missing_ratio(
    *,
    metrics: AlphalensMetricSummary,
    coverage_ratio: float | None,
) -> float | None:
    if metrics.missing_ratio is not None:
        return metrics.missing_ratio
    if coverage_ratio is None:
        return None
    return round(max(1.0 - coverage_ratio, 0.0), 6)


def _build_source_metric_names(*, metrics: AlphalensMetricSummary) -> list[str]:
    source_metric_names: list[str] = []
    if metrics.mean_information_coefficient is not None:
        source_metric_names.append("mean_information_coefficient")
    if metrics.mean_rank_information_coefficient is not None:
        source_metric_names.append("mean_rank_information_coefficient")
    if metrics.information_coefficient_std is not None:
        source_metric_names.append("information_coefficient_std")
    if metrics.information_coefficient_ir is not None:
        source_metric_names.append("information_coefficient_ir")
    if metrics.mean_quantile_return_spread is not None:
        source_metric_names.append("mean_quantile_return_spread")
    return source_metric_names
