from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from quant_ops_api.schemas.factor_validation import PersistenceStatus


TaskLedgerStatus = Literal[
    "created",
    "pending",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "canceled",
]


class TaskLedgerItem(BaseModel):
    task_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=64)
    task_name: str = Field(min_length=1, max_length=256)
    owner: str | None = Field(default=None, max_length=128)
    status: TaskLedgerStatus
    input_params: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    artifact_count: int = Field(ge=0)


class ArtifactLedgerItem(BaseModel):
    artifact_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    artifact_type: str = Field(min_length=1, max_length=64)
    storage_type: str = Field(min_length=1, max_length=32)
    bucket_name: str | None = Field(default=None, max_length=128)
    object_key: str | None = Field(default=None, max_length=1024)
    uri: str | None = Field(default=None, max_length=2048)
    file_size_bytes: int | None = Field(default=None, ge=0)
    schema_version: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ArtifactLedgerResponse(BaseModel):
    generated_at: datetime
    source: str = Field(min_length=1, max_length=128)
    persistence_status: PersistenceStatus
    task_count: int = Field(ge=0)
    artifact_count: int = Field(ge=0)
    tasks: list[TaskLedgerItem] = Field(default_factory=list)
    artifacts: list[ArtifactLedgerItem] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
