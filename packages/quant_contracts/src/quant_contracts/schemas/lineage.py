from datetime import datetime
from typing import Any

from pydantic import Field, field_validator

from quant_contracts.enums import ArtifactType, TaskStatus
from quant_contracts.schemas.common import ContractModel
from quant_contracts.schemas.security import assert_no_secret_keys


class TaskRun(ContractModel):
    task_id: str = Field(min_length=1, max_length=128)
    task_type: str = Field(min_length=1, max_length=64)
    task_name: str = Field(min_length=1, max_length=256)
    owner: str | None = Field(default=None, max_length=128)
    status: TaskStatus = TaskStatus.PENDING
    input_params: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)
    error_message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("input_params", "output_summary")
    @classmethod
    def reject_secret_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        assert_no_secret_keys(value)
        return value


class TaskArtifact(ContractModel):
    artifact_id: str = Field(min_length=1, max_length=128)
    task_id: str = Field(min_length=1, max_length=128)
    artifact_type: ArtifactType = ArtifactType.OTHER
    bucket_name: str | None = Field(default=None, max_length=128)
    object_key: str | None = Field(default=None, max_length=1024)
    uri: str | None = Field(default=None, max_length=2048)
    file_size_bytes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None

    @field_validator("metadata")
    @classmethod
    def reject_secret_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        assert_no_secret_keys(value)
        return value

