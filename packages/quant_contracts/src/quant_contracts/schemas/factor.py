from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from quant_contracts.enums import PriceMode, Timeframe
from quant_contracts.schemas.common import ContractModel
from quant_contracts.schemas.lineage import TaskArtifact, TaskRun


class FactorCalculationRequest(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    symbols: list[str] = Field(min_length=1, max_length=500)
    start: date | str
    end: date | str
    timeframe: Timeframe = Timeframe.DAY_1
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    lookback_window: int = Field(default=20, ge=1, le=252)
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    data_source: str = Field(default="quant_data_hub", min_length=1, max_length=64)
    data_version: str | None = Field(default=None, max_length=128)
    factor_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=100000, ge=1, le=500000)

    @field_validator("factor_name", "universe_name", "data_source", "factor_version", "run_id")
    @classmethod
    def normalize_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("factor_name")
    @classmethod
    def validate_factor_name(cls, value: str) -> str:
        if value.replace("_", "").isalnum() and value[0].isalpha():
            return value.lower()
        raise ValueError("factor_name must use lowercase letters, numbers, and underscores")

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if not normalized_symbols:
            raise ValueError("symbols must not be empty")
        return normalized_symbols

    @model_validator(mode="after")
    def validate_daily_factor_request(self) -> "FactorCalculationRequest":
        if self.timeframe != Timeframe.DAY_1:
            raise ValueError("MVP factor calculation only supports 1d timeframe")
        if self.price_mode != PriceMode.QFQ:
            return self
        if self.batch_id:
            return self
        raise ValueError("batch_id is required when price_mode is qfq")


class FactorDailyValue(ContractModel):
    symbol: str = Field(min_length=1, max_length=32)
    trade_date: date
    factor_name: str = Field(min_length=1, max_length=128)
    factor_value: Decimal | None = None
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    data_source: str = Field(default="quant_data_hub", min_length=1, max_length=64)
    data_version: str | None = Field(default=None, max_length=128)
    factor_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    created_at: datetime | None = None

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        normalized_value = value.strip().upper()
        if normalized_value:
            return normalized_value
        raise ValueError("symbol must not be blank")

    @field_validator("factor_name")
    @classmethod
    def normalize_factor_name(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("factor_name must use lowercase letters, numbers, and underscores")


class FactorCalculationMeta(ContractModel):
    factor_name: str
    timeframe: Timeframe
    price_mode: PriceMode
    row_count: int = Field(ge=0)
    lookback_window: int = Field(ge=1)
    universe_name: str
    data_source: str
    data_version: str | None = None
    factor_version: str
    run_id: str | None = None
    dataset_code: str | None = None
    batch_id: str | None = None


class FactorCalculationResponse(ContractModel):
    meta: FactorCalculationMeta
    rows: list[FactorDailyValue] = Field(default_factory=list)


class FactorValidationRequest(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    factor_values: list[FactorDailyValue] = Field(min_length=1)
    market_start: date | str
    market_end: date | str
    forward_days: int = Field(default=1, ge=1, le=60)
    group_count: int = Field(default=5, ge=2, le=20)
    timeframe: Timeframe = Timeframe.DAY_1
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    limit: int = Field(default=100000, ge=1, le=100000)

    @field_validator("factor_name", "universe_name", "validation_version", "run_id")
    @classmethod
    def normalize_validation_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("factor_name")
    @classmethod
    def validate_validation_factor_name(cls, value: str) -> str:
        normalized_value = value.lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("factor_name must use lowercase letters, numbers, and underscores")

    @model_validator(mode="after")
    def validate_validation_request(self) -> "FactorValidationRequest":
        if self.timeframe != Timeframe.DAY_1:
            raise ValueError("MVP factor validation only supports 1d timeframe")
        if self.price_mode == PriceMode.QFQ and not self.batch_id:
            raise ValueError("batch_id is required when price_mode is qfq")

        invalid_factor_names = [
            value.factor_name for value in self.factor_values if value.factor_name != self.factor_name
        ]
        if invalid_factor_names:
            raise ValueError("all factor_values must match factor_name")

        return self


class FactorIcPoint(ContractModel):
    trade_date: date
    sample_size: int = Field(ge=0)
    ic: float | None = None
    rank_ic: float | None = None


class FactorGroupReturnPoint(ContractModel):
    trade_date: date
    group_index: int = Field(ge=1)
    group_count: int = Field(ge=1)
    sample_size: int = Field(ge=0)
    average_forward_return: float | None = None


class FactorValidationMetric(ContractModel):
    factor_name: str
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    coverage_ratio: float | None = None
    missing_ratio: float | None = None
    ic_mean: float | None = None
    rank_ic_mean: float | None = None
    ic_std: float | None = None
    ic_ir: float | None = None
    group_count: int = Field(default=5, ge=2, le=20)
    group_return_spread_mean: float | None = None
    universe_name: str = "default"
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = None
    batch_id: str | None = None
    validation_version: str = "v1"
    run_id: str | None = None


class FactorValidationFinding(ContractModel):
    severity: Literal["info", "warning", "error"] = "info"
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=256)


class FactorValidationReport(ContractModel):
    decision: Literal[
        "insufficient_data",
        "review_required",
        "candidate_pass",
        "candidate_reject",
    ]
    summary: str = Field(min_length=1, max_length=512)
    findings: list[FactorValidationFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class FactorValidationManifest(ContractModel):
    manifest_id: str = Field(min_length=1, max_length=128)
    schema_version: str = Field(default="factor_validation_manifest.v1", min_length=1, max_length=64)
    task_run: TaskRun
    artifacts: list[TaskArtifact] = Field(default_factory=list)
    persistence_status: Literal["not_persisted", "persisted"] = "not_persisted"
    created_at: datetime | None = None


class FactorValidationResponse(ContractModel):
    metrics: FactorValidationMetric
    ic_series: list[FactorIcPoint] = Field(default_factory=list)
    group_returns: list[FactorGroupReturnPoint] = Field(default_factory=list)
    report: FactorValidationReport | None = None
    manifest: FactorValidationManifest | None = None
