from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ValidationDecision = Literal[
    "insufficient_data",
    "review_required",
    "candidate_pass",
    "candidate_reject",
]
PersistenceStatus = Literal["not_persisted", "persisted"]
FindingSeverity = Literal["info", "warning", "error"]


class FactorValidationMetricSummary(BaseModel):
    factor_name: str = Field(min_length=1, max_length=128)
    validation_version: str = Field(min_length=1, max_length=64)
    run_id: str = Field(min_length=1, max_length=128)
    forward_days: int = Field(ge=1)
    sample_count: int = Field(ge=0)
    effective_sample_count: int = Field(ge=0)
    coverage_ratio: float | None = None
    missing_ratio: float | None = None
    ic_mean: float | None = None
    rank_ic_mean: float | None = None
    ic_ir: float | None = None
    group_count: int = Field(default=5, ge=2, le=20)
    group_return_spread_mean: float | None = None
    decision: ValidationDecision


class FactorValidationFindingSummary(BaseModel):
    severity: FindingSeverity
    code: str = Field(min_length=1, max_length=64)
    message: str = Field(min_length=1, max_length=256)


class FactorValidationArtifactSummary(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=128)
    artifact_type: str = Field(min_length=1, max_length=64)
    object_key: str | None = Field(default=None, max_length=1024)
    schema_version: str = Field(min_length=1, max_length=64)
    persistence_status: PersistenceStatus


class FactorScoreComponentSummary(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    raw_value: float | None = None
    score: float
    max_score: float = Field(ge=0)
    reason: str = Field(min_length=1, max_length=256)


class FactorScoreCardSummary(BaseModel):
    factor_name: str = Field(min_length=1, max_length=128)
    evaluation_engine: str = Field(min_length=1, max_length=64)
    final_score: float = Field(ge=0, le=100)
    max_score: float = Field(default=100, ge=1, le=100)
    review_decision: ValidationDecision
    score_components: list[FactorScoreComponentSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class FactorComparisonSummary(BaseModel):
    primary_engine: str = Field(min_length=1, max_length=64)
    engine_count: int = Field(ge=0)
    has_engine_disagreement: bool = False
    comparison_summary: str = Field(min_length=1, max_length=512)


class FactorValidationManifestSummary(BaseModel):
    manifest_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    task_name: str = Field(min_length=1, max_length=256)
    task_type: str = Field(min_length=1, max_length=64)
    persistence_status: PersistenceStatus
    artifact_count: int = Field(ge=0)
    artifacts: list[FactorValidationArtifactSummary] = Field(default_factory=list)


class FactorValidationReviewResponse(BaseModel):
    generated_at: datetime
    source: str = Field(min_length=1, max_length=128)
    persistence_status: PersistenceStatus
    latest_metric: FactorValidationMetricSummary
    findings: list[FactorValidationFindingSummary] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    score_card: FactorScoreCardSummary | None = None
    comparison: FactorComparisonSummary | None = None
    manifest: FactorValidationManifestSummary
    limitations: list[str] = Field(default_factory=list)
