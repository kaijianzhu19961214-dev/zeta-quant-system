from pydantic import Field
from quant_contracts import QfqBatch
from quant_contracts.schemas.common import ContractModel


class QfqBatchListResponse(ContractModel):
    row_count: int = Field(ge=0)
    batches: list[QfqBatch] = Field(default_factory=list)

