from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from quant_contracts import AlgorithmSpec

from quant_ops_api.api.v1.dependencies import get_factor_lab_client
from quant_ops_api.clients import FactorLabClient, FactorLabClientError

router = APIRouter(prefix="/api/v1/factor-lab", tags=["factor-lab"])


@router.get("/algorithms", response_model=list[AlgorithmSpec])
async def read_factor_lab_algorithms(
    factor_lab_client: Annotated[FactorLabClient, Depends(get_factor_lab_client)],
) -> list[AlgorithmSpec]:
    try:
        return await factor_lab_client.list_algorithms()
    except FactorLabClientError as error:
        if error.status_code == status.HTTP_504_GATEWAY_TIMEOUT:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error
