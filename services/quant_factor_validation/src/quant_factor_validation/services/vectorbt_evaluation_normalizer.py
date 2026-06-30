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


class VectorbtMetricPayload(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    metric_values: dict[str, ExternalMetricValue] = Field(default_factory=dict)
    asset_class: AssetClass = AssetClass.FUTURES
    factor_mode: FactorMode = FactorMode.TIME_SERIES
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    group_count: int = Field(default=2, ge=2, le=20)
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    portfolio_name: str | None = Field(default=None, max_length=128)
    parameter_set_id: str | None = Field(default=None, max_length=128)
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
        "portfolio_name",
        "parameter_set_id",
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
    def validate_metric_payload(self) -> "VectorbtMetricPayload":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


class VectorbtMetricSummary(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    total_return: float | None = None
    annualized_return: float | None = None
    sharpe_ratio: float | None = None
    sortino_ratio: float | None = None
    max_drawdown: float | None = None
    turnover_ratio: float | None = None
    trade_count: int | None = Field(default=None, ge=0)
    win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    missing_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    asset_class: AssetClass = AssetClass.FUTURES
    factor_mode: FactorMode = FactorMode.TIME_SERIES
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    group_count: int = Field(default=2, ge=2, le=20)
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    portfolio_name: str | None = Field(default=None, max_length=128)
    parameter_set_id: str | None = Field(default=None, max_length=128)
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
        "portfolio_name",
        "parameter_set_id",
    )
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        return normalize_optional_text(value=value)

    @field_validator("warnings", "notes")
    @classmethod
    def normalize_text_list(cls, value: list[str]) -> list[str]:
        return normalize_text_list(value=value)

    @model_validator(mode="after")
    def validate_metric_summary(self) -> "VectorbtMetricSummary":
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


def build_vectorbt_metric_summary_from_payload(
    *,
    payload: VectorbtMetricPayload,
) -> VectorbtMetricSummary:
    return VectorbtMetricSummary(
        factor_name=payload.factor_name,
        start_date=payload.start_date,
        end_date=payload.end_date,
        forward_days=payload.forward_days,
        sample_count=payload.sample_count,
        effective_sample_count=payload.effective_sample_count,
        total_return=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_TOTAL_RETURN_ALIASES,
        ),
        annualized_return=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_ANNUALIZED_RETURN_ALIASES,
        ),
        sharpe_ratio=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_SHARPE_RATIO_ALIASES,
        ),
        sortino_ratio=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_SORTINO_RATIO_ALIASES,
        ),
        max_drawdown=find_optional_float(
            metric_values=payload.metric_values,
            aliases=_MAX_DRAWDOWN_ALIASES,
        ),
        turnover_ratio=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_TURNOVER_RATIO_ALIASES,
        ),
        trade_count=find_optional_int(
            metric_values=payload.metric_values,
            aliases=_TRADE_COUNT_ALIASES,
        ),
        win_rate=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_WIN_RATE_ALIASES,
        ),
        coverage_ratio=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_COVERAGE_RATIO_ALIASES,
        ),
        missing_ratio=find_optional_ratio(
            metric_values=payload.metric_values,
            aliases=_MISSING_RATIO_ALIASES,
        ),
        asset_class=payload.asset_class,
        factor_mode=payload.factor_mode,
        factor_family=payload.factor_family,
        group_count=payload.group_count,
        universe_name=payload.universe_name,
        price_mode=payload.price_mode,
        dataset_code=payload.dataset_code,
        batch_id=payload.batch_id,
        validation_version=payload.validation_version,
        run_id=payload.run_id,
        source_version=payload.source_version,
        source_run_id=payload.source_run_id or payload.parameter_set_id,
        portfolio_name=payload.portfolio_name,
        parameter_set_id=payload.parameter_set_id,
        warnings=payload.warnings,
        notes=payload.notes,
    )


def run_vectorbt_payload_evaluation(
    *,
    payload: VectorbtMetricPayload,
) -> FactorEvaluationResult:
    metrics = build_vectorbt_metric_summary_from_payload(payload=payload)
    return build_vectorbt_factor_evaluation_result(metrics=metrics)


def build_vectorbt_external_summary(
    *,
    metrics: VectorbtMetricSummary,
) -> ExternalFactorValidationSummary:
    coverage_ratio = _resolve_coverage_ratio(metrics=metrics)
    missing_ratio = _resolve_missing_ratio(metrics=metrics, coverage_ratio=coverage_ratio)

    return ExternalFactorValidationSummary(
        factor_name=metrics.factor_name,
        asset_class=metrics.asset_class,
        factor_mode=metrics.factor_mode,
        factor_family=metrics.factor_family,
        evaluation_engine=EvaluationEngine.VECTORBT,
        start_date=metrics.start_date,
        end_date=metrics.end_date,
        forward_days=metrics.forward_days,
        sample_count=metrics.sample_count,
        effective_sample_count=metrics.effective_sample_count,
        coverage_ratio=coverage_ratio,
        missing_ratio=missing_ratio,
        group_count=metrics.group_count,
        group_return_spread_mean=_resolve_standard_return(metrics=metrics),
        universe_name=metrics.universe_name,
        price_mode=metrics.price_mode,
        dataset_code=metrics.dataset_code,
        batch_id=metrics.batch_id,
        validation_version=metrics.validation_version,
        run_id=metrics.run_id,
        source_library="vectorbt",
        source_version=metrics.source_version,
        source_run_id=metrics.source_run_id,
        source_metric_names=_build_source_metric_names(metrics=metrics),
        warnings=metrics.warnings,
        notes=_build_summary_notes(metrics=metrics),
    )


def build_vectorbt_factor_evaluation_result(
    *,
    metrics: VectorbtMetricSummary,
) -> FactorEvaluationResult:
    summary = build_vectorbt_external_summary(metrics=metrics)
    return build_external_factor_evaluation_result(summary=summary)


def _resolve_coverage_ratio(*, metrics: VectorbtMetricSummary) -> float | None:
    if metrics.coverage_ratio is not None:
        return metrics.coverage_ratio
    if metrics.sample_count == 0:
        return None
    return round(metrics.effective_sample_count / metrics.sample_count, 6)


def _resolve_missing_ratio(
    *,
    metrics: VectorbtMetricSummary,
    coverage_ratio: float | None,
) -> float | None:
    if metrics.missing_ratio is not None:
        return metrics.missing_ratio
    if coverage_ratio is None:
        return None
    return round(max(1.0 - coverage_ratio, 0.0), 6)


def _resolve_standard_return(*, metrics: VectorbtMetricSummary) -> float | None:
    if metrics.annualized_return is not None:
        return metrics.annualized_return
    return metrics.total_return


def _build_source_metric_names(*, metrics: VectorbtMetricSummary) -> list[str]:
    source_metric_names: list[str] = []
    if metrics.total_return is not None:
        source_metric_names.append("vectorbt_total_return")
    if metrics.annualized_return is not None:
        source_metric_names.append("vectorbt_annualized_return")
    if metrics.sharpe_ratio is not None:
        source_metric_names.append("vectorbt_sharpe_ratio")
    if metrics.max_drawdown is not None:
        source_metric_names.append("vectorbt_max_drawdown")
    if metrics.turnover_ratio is not None:
        source_metric_names.append("vectorbt_turnover_ratio")
    if metrics.trade_count is not None:
        source_metric_names.append("vectorbt_trade_count")
    if metrics.win_rate is not None:
        source_metric_names.append("vectorbt_win_rate")
    return source_metric_names


def _build_summary_notes(*, metrics: VectorbtMetricSummary) -> list[str]:
    notes = [*metrics.notes]
    for name, value in _build_backtest_metric_notes(metrics=metrics):
        notes.append(f"{name}={value}")
    if metrics.portfolio_name:
        notes.append(f"vectorbt_portfolio_name={metrics.portfolio_name}")
    if metrics.parameter_set_id:
        notes.append(f"vectorbt_parameter_set_id={metrics.parameter_set_id}")
    return notes


def _build_backtest_metric_notes(
    *,
    metrics: VectorbtMetricSummary,
) -> list[tuple[str, float | int]]:
    metric_notes: list[tuple[str, float | int]] = []
    if metrics.total_return is not None:
        metric_notes.append(("vectorbt_total_return", metrics.total_return))
    if metrics.annualized_return is not None:
        metric_notes.append(("vectorbt_annualized_return", metrics.annualized_return))
    if metrics.sharpe_ratio is not None:
        metric_notes.append(("vectorbt_sharpe_ratio", metrics.sharpe_ratio))
    if metrics.sortino_ratio is not None:
        metric_notes.append(("vectorbt_sortino_ratio", metrics.sortino_ratio))
    if metrics.max_drawdown is not None:
        metric_notes.append(("vectorbt_max_drawdown", metrics.max_drawdown))
    if metrics.turnover_ratio is not None:
        metric_notes.append(("vectorbt_turnover_ratio", metrics.turnover_ratio))
    if metrics.trade_count is not None:
        metric_notes.append(("vectorbt_trade_count", metrics.trade_count))
    if metrics.win_rate is not None:
        metric_notes.append(("vectorbt_win_rate", metrics.win_rate))
    return metric_notes


_TOTAL_RETURN_ALIASES = (
    "total_return",
    "Total Return",
    "return",
    "portfolio_return",
    "cumulative_return",
)
_ANNUALIZED_RETURN_ALIASES = (
    "annualized_return",
    "annual_return",
    "ann_return",
    "Annualized Return",
)
_SHARPE_RATIO_ALIASES = (
    "sharpe",
    "sharpe_ratio",
    "Sharpe Ratio",
)
_SORTINO_RATIO_ALIASES = (
    "sortino",
    "sortino_ratio",
    "Sortino Ratio",
)
_MAX_DRAWDOWN_ALIASES = (
    "max_drawdown",
    "max_dd",
    "Max Drawdown",
)
_TURNOVER_RATIO_ALIASES = (
    "turnover",
    "turnover_ratio",
    "annual_turnover",
)
_TRADE_COUNT_ALIASES = (
    "trade_count",
    "trades",
    "total_trades",
    "Total Trades",
)
_WIN_RATE_ALIASES = (
    "win_rate",
    "Win Rate",
    "winning_rate",
)
_COVERAGE_RATIO_ALIASES = (
    "coverage_ratio",
    "coverage",
    "signal_coverage",
)
_MISSING_RATIO_ALIASES = (
    "missing_ratio",
    "missing",
    "signal_missing_ratio",
)
