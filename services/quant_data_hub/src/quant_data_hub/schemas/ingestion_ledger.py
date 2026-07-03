from datetime import date, datetime, timezone
from typing import Literal

from pydantic import Field
from quant_contracts import Timeframe
from quant_contracts.schemas.common import ContractModel


IngestionPersistenceStatus = Literal["not_persisted", "persisted"]
IngestionRunStatus = Literal["succeeded", "review_required", "failed"]
IngestionQualityCheckStatus = Literal["passed", "warning", "failed"]


class IngestionRunRecord(ContractModel):
    run_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=64)
    source_name: str = Field(min_length=1, max_length=128)
    dataset_code: str = Field(min_length=1, max_length=128)
    timeframe: Timeframe
    status: IngestionRunStatus
    storage_target: str = Field(min_length=1, max_length=128)
    start_date: date | None = None
    end_date: date | None = None
    row_count: int = Field(ge=0)
    symbol_count: int = Field(ge=0)
    trading_day_count: int = Field(ge=0)
    duplicate_key_rows: int = Field(ge=0)
    output_summary: dict[str, int | str | None] = Field(default_factory=dict)
    finished_at: datetime | None = None


class IngestionQualityCheckRecord(ContractModel):
    check_id: str = Field(min_length=1, max_length=128)
    run_id: str = Field(min_length=1, max_length=128)
    check_name: str = Field(min_length=1, max_length=128)
    check_status: IngestionQualityCheckStatus
    expected_condition: str = Field(min_length=1, max_length=256)
    observed_value: str | None = None
    details: str | None = None


class IngestionLedgerPreviewResponse(ContractModel):
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    persistence_status: IngestionPersistenceStatus
    run_count: int = Field(ge=0)
    quality_check_count: int = Field(ge=0)
    runs: list[IngestionRunRecord] = Field(default_factory=list)
    quality_checks: list[IngestionQualityCheckRecord] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
