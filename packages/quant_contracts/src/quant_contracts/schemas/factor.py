from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, field_validator, model_validator

from quant_contracts.enums import AssetClass, EvaluationEngine, FactorFamily, FactorMode, PriceMode, Timeframe
from quant_contracts.schemas.common import ContractModel
from quant_contracts.schemas.lineage import TaskArtifact, TaskRun


FactorReviewDecision = Literal[
    "insufficient_data",
    "review_required",
    "candidate_pass",
    "candidate_reject",
]
AlgorithmRole = Literal[
    "factor_generator",
    "model",
    "validation_engine",
    "comparison_engine",
]
AlgorithmStatus = Literal["available", "planned", "disabled", "deprecated"]
AlgorithmOutputKind = Literal[
    "factor_values",
    "forecast",
    "volatility",
    "signal",
    "diagnostics",
]
AlgorithmParameterValueType = Literal["integer", "number", "string", "boolean"]
AlgorithmReviewGateCategory = Literal[
    "hypothesis",
    "data",
    "construction",
    "leakage",
    "validation",
    "operations",
]
AlgorithmReviewGateStatus = Literal["satisfied", "missing", "not_applicable"]
AlgorithmReviewEvidenceType = Literal[
    "research_note",
    "notebook",
    "artifact",
    "validation_report",
    "external_link",
    "manual_note",
]
AlgorithmReviewEvidenceStatus = Literal["submitted", "accepted", "rejected"]
AlgorithmReviewEvidencePersistenceStatus = Literal["not_persisted", "persisted"]


class AlgorithmParameterSpec(ContractModel):
    name: str = Field(min_length=1, max_length=64)
    value_type: AlgorithmParameterValueType
    description: str = Field(min_length=1, max_length=256)
    default_value: int | float | str | bool | None = None
    minimum: float | None = None
    maximum: float | None = None

    @field_validator("name")
    @classmethod
    def validate_parameter_name(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("parameter name must use lowercase letters, numbers, and underscores")


class AlgorithmCapability(ContractModel):
    asset_classes: list[AssetClass] = Field(min_length=1)
    factor_modes: list[FactorMode] = Field(min_length=1)
    factor_families: list[FactorFamily] = Field(min_length=1)
    timeframes: list[Timeframe] = Field(min_length=1)
    output_kinds: list[AlgorithmOutputKind] = Field(min_length=1)


class AlgorithmReviewGate(ContractModel):
    gate_id: str = Field(min_length=1, max_length=64)
    category: AlgorithmReviewGateCategory
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(min_length=1, max_length=512)
    status: AlgorithmReviewGateStatus = "missing"
    evidence: str | None = Field(default=None, max_length=512)
    is_required: bool = True

    @field_validator("gate_id")
    @classmethod
    def validate_gate_id(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("gate_id must use lowercase letters, numbers, and underscores")

    @field_validator("title", "description", "evidence")
    @classmethod
    def normalize_review_gate_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")


class AlgorithmReviewGateEvidenceSubmission(ContractModel):
    algorithm_id: str = Field(min_length=1, max_length=128)
    gate_id: str = Field(min_length=1, max_length=64)
    submitted_by: str = Field(min_length=1, max_length=128)
    evidence_type: AlgorithmReviewEvidenceType
    evidence_source: str = Field(min_length=1, max_length=256)
    summary: str = Field(min_length=1, max_length=1024)
    artifact_id: str | None = Field(default=None, max_length=128)
    artifact_uri: str | None = Field(default=None, max_length=512)
    source_url: str | None = Field(default=None, max_length=512)
    notes: list[str] = Field(default_factory=list)

    @field_validator("algorithm_id")
    @classmethod
    def validate_submission_algorithm_id(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        comparable_value = normalized_value.replace(".", "_").replace("-", "_")
        if comparable_value.replace("_", "").isalnum() and comparable_value[0].isalpha():
            return normalized_value
        raise ValueError("algorithm_id must use lowercase letters, numbers, underscores, dashes, and dots")

    @field_validator("gate_id")
    @classmethod
    def validate_submission_gate_id(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        if normalized_value.replace("_", "").isalnum() and normalized_value[0].isalpha():
            return normalized_value
        raise ValueError("gate_id must use lowercase letters, numbers, and underscores")

    @field_validator("submitted_by", "evidence_source", "summary", "artifact_id", "artifact_uri", "source_url")
    @classmethod
    def normalize_submission_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("notes")
    @classmethod
    def normalize_submission_notes(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class AlgorithmReviewGateEvidenceRecord(AlgorithmReviewGateEvidenceSubmission):
    evidence_id: str = Field(min_length=1, max_length=128)
    gate_category: AlgorithmReviewGateCategory
    gate_title: str = Field(min_length=1, max_length=128)
    previous_gate_status: AlgorithmReviewGateStatus
    evidence_status: AlgorithmReviewEvidenceStatus = "submitted"
    submitted_at: datetime
    reviewed_by: str | None = Field(default=None, max_length=128)
    reviewed_at: datetime | None = None
    review_comment: str | None = Field(default=None, max_length=512)
    is_required: bool = True

    @field_validator("evidence_id")
    @classmethod
    def validate_evidence_id(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        comparable_value = normalized_value.replace("-", "_")
        if comparable_value.replace("_", "").isalnum() and comparable_value[0].isalpha():
            return normalized_value
        raise ValueError("evidence_id must use lowercase letters, numbers, underscores, and dashes")

    @field_validator("gate_title", "reviewed_by", "review_comment")
    @classmethod
    def normalize_record_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")


class AlgorithmReviewGateEvidenceResponse(ContractModel):
    record: AlgorithmReviewGateEvidenceRecord
    persistence_status: AlgorithmReviewEvidencePersistenceStatus = "not_persisted"
    limitations: list[str] = Field(default_factory=list)

    @field_validator("limitations")
    @classmethod
    def normalize_limitations(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]


class AlgorithmSpec(ContractModel):
    algorithm_id: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    role: AlgorithmRole = "factor_generator"
    status: AlgorithmStatus = "available"
    version: str = Field(default="v1", min_length=1, max_length=64)
    description: str = Field(min_length=1, max_length=512)
    source_library: str | None = Field(default=None, max_length=64)
    source_url: str | None = Field(default=None, max_length=512)
    adapter_module: str | None = Field(default=None, max_length=256)
    capability: AlgorithmCapability
    parameters: list[AlgorithmParameterSpec] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    research_notes: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    review_gates: list[AlgorithmReviewGate] = Field(default_factory=list)

    @field_validator("algorithm_id")
    @classmethod
    def validate_algorithm_id(cls, value: str) -> str:
        normalized_value = value.strip().lower()
        comparable_value = normalized_value.replace(".", "_").replace("-", "_")
        if comparable_value.replace("_", "").isalnum() and comparable_value[0].isalpha():
            return normalized_value
        raise ValueError("algorithm_id must use lowercase letters, numbers, underscores, dashes, and dots")

    @field_validator(
        "display_name",
        "version",
        "description",
        "source_library",
        "source_url",
        "adapter_module",
    )
    @classmethod
    def normalize_algorithm_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("tags", "research_notes", "limitations")
    @classmethod
    def normalize_algorithm_text_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_available_algorithm_review_gates(self) -> "AlgorithmSpec":
        if self.status != "available":
            return self

        missing_gate_ids = [
            gate.gate_id
            for gate in self.review_gates
            if gate.is_required and gate.status == "missing"
        ]
        if not missing_gate_ids:
            return self
        raise ValueError("available algorithm must not have missing required review gates")


class FactorCalculationRequest(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    algorithm_id: str | None = Field(default=None, max_length=128)
    algorithm_parameters: dict[str, int | float | str | bool] = Field(default_factory=dict)
    symbols: list[str] = Field(min_length=1, max_length=500)
    start: date | str
    end: date | str
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
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

    @field_validator("factor_name", "algorithm_id", "universe_name", "data_source", "factor_version", "run_id")
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

    @field_validator("algorithm_id")
    @classmethod
    def validate_calculation_algorithm_id(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.lower()
        comparable_value = normalized_value.replace(".", "_").replace("-", "_")
        if comparable_value.replace("_", "").isalnum() and comparable_value[0].isalpha():
            return normalized_value
        raise ValueError("algorithm_id must use lowercase letters, numbers, underscores, dashes, and dots")

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
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
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
    algorithm_id: str | None = None
    algorithm_version: str | None = None
    algorithm_source_library: str | None = None
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
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
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    evaluation_engine: EvaluationEngine = EvaluationEngine.INTERNAL
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

        invalid_factor_classifications = [
            value
            for value in self.factor_values
            if value.asset_class != self.asset_class
            or value.factor_mode != self.factor_mode
            or value.factor_family != self.factor_family
        ]
        if invalid_factor_classifications:
            raise ValueError("all factor_values must match asset_class, factor_mode, and factor_family")

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
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    evaluation_engine: EvaluationEngine = EvaluationEngine.INTERNAL
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


class ExternalFactorValidationSummary(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    evaluation_engine: EvaluationEngine
    start_date: date
    end_date: date
    forward_days: int = Field(ge=1, le=60)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    coverage_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    missing_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    ic_mean: float | None = Field(default=None, ge=-1.0, le=1.0)
    rank_ic_mean: float | None = Field(default=None, ge=-1.0, le=1.0)
    ic_std: float | None = Field(default=None, ge=0.0)
    ic_ir: float | None = None
    group_count: int = Field(default=5, ge=2, le=20)
    group_return_spread_mean: float | None = None
    universe_name: str = Field(default="default", min_length=1, max_length=128)
    price_mode: PriceMode = PriceMode.RAW
    dataset_code: str | None = Field(default=None, max_length=128)
    batch_id: str | None = Field(default=None, max_length=128)
    validation_version: str = Field(default="v1", min_length=1, max_length=64)
    run_id: str | None = Field(default=None, max_length=128)
    source_library: str = Field(min_length=1, max_length=64)
    source_version: str | None = Field(default=None, max_length=64)
    source_run_id: str | None = Field(default=None, max_length=128)
    source_metric_names: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("factor_name")
    @classmethod
    def validate_external_factor_name(cls, value: str) -> str:
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
        "source_library",
        "source_version",
        "source_run_id",
    )
    @classmethod
    def normalize_external_text(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized_value = value.strip()
        if normalized_value:
            return normalized_value
        raise ValueError("value must not be blank")

    @field_validator("source_metric_names", "warnings", "notes")
    @classmethod
    def normalize_external_text_list(cls, value: list[str]) -> list[str]:
        return [item.strip() for item in value if item.strip()]

    @model_validator(mode="after")
    def validate_external_summary(self) -> "ExternalFactorValidationSummary":
        if self.evaluation_engine == EvaluationEngine.INTERNAL:
            raise ValueError("external validation summary must use a non-internal evaluation_engine")
        if self.end_date < self.start_date:
            raise ValueError("end_date must be greater than or equal to start_date")
        if self.effective_sample_count > self.sample_count:
            raise ValueError("effective_sample_count must not exceed sample_count")
        return self


class FactorValidationFinding(ContractModel):
    severity: Literal["info", "warning", "error"] = "info"
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=256)


class FactorValidationReport(ContractModel):
    decision: FactorReviewDecision
    summary: str = Field(min_length=1, max_length=512)
    findings: list[FactorValidationFinding] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)


class FactorScoreComponent(ContractModel):
    name: str = Field(min_length=1, max_length=64)
    raw_value: float | None = None
    score: float = Field(ge=-100, le=100)
    max_score: float = Field(default=100, ge=0, le=100)
    reason: str = Field(min_length=1, max_length=256)


class FactorScoreCard(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    evaluation_engine: EvaluationEngine = EvaluationEngine.INTERNAL
    final_score: float = Field(ge=0, le=100)
    max_score: float = Field(default=100, ge=1, le=100)
    review_decision: FactorReviewDecision
    score_components: list[FactorScoreComponent] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FactorEvaluationResult(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    asset_class: AssetClass = AssetClass.EQUITY
    factor_mode: FactorMode = FactorMode.CROSS_SECTIONAL
    factor_family: FactorFamily = FactorFamily.PRICE_VOLUME
    evaluation_engine: EvaluationEngine = EvaluationEngine.INTERNAL
    metrics: FactorValidationMetric
    report: FactorValidationReport | None = None
    score_card: FactorScoreCard | None = None


class FactorComparisonReport(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    primary_engine: EvaluationEngine = EvaluationEngine.INTERNAL
    engine_results: list[FactorEvaluationResult] = Field(default_factory=list)
    engine_count: int = Field(default=0, ge=0)
    has_engine_disagreement: bool = False
    comparison_summary: str = Field(min_length=1, max_length=512)


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
    evaluation_result: FactorEvaluationResult | None = None
    score_card: FactorScoreCard | None = None
    comparison_report: FactorComparisonReport | None = None
    manifest: FactorValidationManifest | None = None
