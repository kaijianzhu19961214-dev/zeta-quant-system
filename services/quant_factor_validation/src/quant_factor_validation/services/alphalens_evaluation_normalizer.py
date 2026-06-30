from datetime import date
from math import isfinite
from typing import TypeAlias

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


AlphalensMetricValue: TypeAlias = float | int | str | None


class AlphalensMetricPayload(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    metric_values: dict[str, AlphalensMetricValue] = Field(default_factory=dict)
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
        return _normalize_factor_name(value=value)

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
        return _normalize_optional_text(value=value)

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return _normalize_text_list(value=value)

    @field_validator("metric_values")
    @classmethod
    def normalize_metric_values(
        cls,
        value: dict[str, AlphalensMetricValue],
    ) -> dict[str, AlphalensMetricValue]:
        normalized_values: dict[str, AlphalensMetricValue] = {}
        for metric_name, metric_value in value.items():
            normalized_metric_name = metric_name.strip()
            if not normalized_metric_name:
                raise ValueError("metric_values keys must not be blank")
            normalized_values[normalized_metric_name] = metric_value
        return normalized_values

    @model_validator(mode="after")
    def validate_metric_payload(self) -> "AlphalensMetricPayload":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


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
        return _normalize_factor_name(value=value)

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
        return _normalize_optional_text(value=value)

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return _normalize_text_list(value=value)

    @model_validator(mode="after")
    def validate_metric_summary(self) -> "AlphalensMetricSummary":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


def build_alphalens_metric_summary_from_payload(
    *,
    payload: AlphalensMetricPayload,
) -> AlphalensMetricSummary:
    return AlphalensMetricSummary(
        factor_name=payload.factor_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        forward_days=payload.forward_days,
        sample_count=payload.sample_count,
        effective_sample_count=payload.effective_sample_count,
        mean_information_coefficient=_find_optional_float(
            payload=payload,
            aliases=_MEAN_IC_ALIASES,
        ),
        mean_rank_information_coefficient=_find_optional_float(
            payload=payload,
            aliases=_MEAN_RANK_IC_ALIASES,
        ),
        information_coefficient_std=_find_optional_float(
            payload=payload,
            aliases=_IC_STD_ALIASES,
        ),
        information_coefficient_ir=_find_optional_float(
            payload=payload,
            aliases=_IC_IR_ALIASES,
        ),
        mean_quantile_return_spread=_find_optional_float(
            payload=payload,
            aliases=_QUANTILE_SPREAD_ALIASES,
        ),
        coverage_ratio=_find_optional_ratio(
            payload=payload,
            aliases=_COVERAGE_RATIO_ALIASES,
        ),
        missing_ratio=_find_optional_ratio(
            payload=payload,
            aliases=_MISSING_RATIO_ALIASES,
        ),
        group_count=_find_optional_int(
            payload=payload,
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
        source_run_id=payload.source_run_id,
        warnings=payload.warnings,
        notes=payload.notes,
    )


def run_alphalens_payload_evaluation(
    *,
    payload: AlphalensMetricPayload,
) -> FactorEvaluationResult:
    metrics = build_alphalens_metric_summary_from_payload(payload=payload)
    return build_alphalens_factor_evaluation_result(metrics=metrics)


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


_MEAN_IC_ALIASES = (
    "mean_information_coefficient",
    "mean_ic",
    "ic_mean",
    "mean_ic_1d",
    "mean_ic_5d",
    "IC Mean",
)
_MEAN_RANK_IC_ALIASES = (
    "mean_rank_information_coefficient",
    "mean_rank_ic",
    "rank_ic_mean",
    "mean_rank_ic_1d",
    "mean_rank_ic_5d",
    "Rank IC Mean",
)
_IC_STD_ALIASES = (
    "information_coefficient_std",
    "ic_std",
    "IC Std.",
)
_IC_IR_ALIASES = (
    "information_coefficient_ir",
    "ic_ir",
    "IC IR",
    "risk_adjusted_ic",
)
_QUANTILE_SPREAD_ALIASES = (
    "mean_quantile_return_spread",
    "mean_quantile_returns_spread",
    "quantile_return_spread_mean",
    "mean_return_spread",
    "mean_period_wise_return_spread",
)
_COVERAGE_RATIO_ALIASES = (
    "coverage_ratio",
    "coverage",
    "factor_coverage",
)
_MISSING_RATIO_ALIASES = (
    "missing_ratio",
    "missing",
    "missing_factor_ratio",
)
_GROUP_COUNT_ALIASES = (
    "group_count",
    "quantile_count",
    "quantiles",
)


def _find_optional_float(
    *,
    payload: AlphalensMetricPayload,
    aliases: tuple[str, ...],
) -> float | None:
    value = _find_metric_value(payload=payload, aliases=aliases)
    if value is None:
        return None
    return _coerce_optional_float(value=value)


def _find_optional_ratio(
    *,
    payload: AlphalensMetricPayload,
    aliases: tuple[str, ...],
) -> float | None:
    value = _find_optional_float(payload=payload, aliases=aliases)
    if value is None:
        return None
    if value > 1.0:
        return value / 100.0
    return value


def _find_optional_int(
    *,
    payload: AlphalensMetricPayload,
    aliases: tuple[str, ...],
) -> int | None:
    value = _find_metric_value(payload=payload, aliases=aliases)
    if value is None:
        return None
    numeric_value = _coerce_optional_float(value=value)
    if numeric_value is None:
        return None
    return int(numeric_value)


def _find_metric_value(
    *,
    payload: AlphalensMetricPayload,
    aliases: tuple[str, ...],
) -> AlphalensMetricValue:
    lower_metric_values = {
        metric_name.lower(): metric_value
        for metric_name, metric_value in payload.metric_values.items()
    }
    for alias in aliases:
        metric_value = lower_metric_values.get(alias.lower())
        if metric_value is not None:
            return metric_value
    return None


def _coerce_optional_float(*, value: AlphalensMetricValue) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("metric value must be numeric, not boolean")
    if isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        normalized_value = value.strip()
        if not normalized_value:
            return None
        if normalized_value.endswith("%"):
            numeric_value = float(normalized_value[:-1]) / 100.0
        else:
            numeric_value = float(normalized_value)

    if not isfinite(numeric_value):
        return None
    return numeric_value


def _normalize_factor_name(*, value: str) -> str:
    normalized_value = value.strip().lower()
    if (
        normalized_value
        and normalized_value.replace("_", "").isalnum()
        and normalized_value[0].isalpha()
    ):
        return normalized_value
    raise ValueError("factor_name must use lowercase letters, numbers, and underscores")


def _normalize_optional_text(*, value: str | None) -> str | None:
    if value is None:
        return value

    normalized_value = value.strip()
    if normalized_value:
        return normalized_value
    raise ValueError("value must not be blank")


def _normalize_text_list(*, value: list[str]) -> list[str]:
    return [item.strip() for item in value if item.strip()]
