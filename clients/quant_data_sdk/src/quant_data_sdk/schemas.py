from pydantic import Field
from quant_contracts import QfqBatch
from quant_contracts.schemas.common import ContractModel


class HealthResponse(ContractModel):
    status: str = Field(min_length=1, max_length=64)
    service: str = Field(min_length=1, max_length=128)


class QfqBatchListResponse(ContractModel):
    row_count: int = Field(ge=0)
    batches: list[QfqBatch] = Field(default_factory=list)
