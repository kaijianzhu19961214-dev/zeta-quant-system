from datetime import date, datetime

from pydantic import Field, field_validator

from quant_contracts.schemas.common import ContractModel


class QfqBatch(ContractModel):
    batch_id: str = Field(min_length=1, max_length=128)
    qfq_base_date: date
    status: str = Field(min_length=1, max_length=64)
    description: str | None = None
    created_at: datetime | None = None
    finished_at: datetime | None = None

    @field_validator("batch_id", "status")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError("value must not be blank")
        return normalized_value

