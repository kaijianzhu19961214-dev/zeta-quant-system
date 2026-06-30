from typing import Annotated

from fastapi import APIRouter, Depends

from quant_ops_api.api.v1.dependencies import get_artifact_ledger_service
from quant_ops_api.schemas import ArtifactLedgerResponse
from quant_ops_api.services import ArtifactLedgerService

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])


@router.get("/ledger", response_model=ArtifactLedgerResponse)
async def read_artifact_ledger(
    ledger_service: Annotated[ArtifactLedgerService, Depends(get_artifact_ledger_service)],
) -> ArtifactLedgerResponse:
    return await ledger_service.get_ledger()
