from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from quant_contracts import FactorComparisonReport

from quant_ops_api.api.v1.dependencies import (
    get_artifact_ledger_service,
    get_factor_comparison_artifact_service,
    get_factor_validation_client,
    get_factor_validation_review_service,
)
from quant_ops_api.clients import FactorValidationClient, FactorValidationClientError
from quant_ops_api.schemas import (
    FactorComparisonArtifactReference,
    ExternalPayloadComparisonPreviewResponse,
    ExternalPayloadComparisonRequest,
    FactorValidationReviewResponse,
)
from quant_ops_api.services import (
    ArtifactLedgerService,
    FactorComparisonArtifactService,
    FactorValidationReviewService,
)
from quant_ops_api.services.factor_comparison_artifact_service import FactorComparisonArtifactReadResult

router = APIRouter(prefix="/api/v1/factor-validation", tags=["factor-validation"])


@router.get("/review", response_model=FactorValidationReviewResponse)
def read_factor_validation_review(
    review_service: Annotated[
        FactorValidationReviewService,
        Depends(get_factor_validation_review_service),
    ],
) -> FactorValidationReviewResponse:
    return review_service.get_review()


@router.get("/external-payloads/preview", response_model=ExternalPayloadComparisonPreviewResponse)
async def read_external_payload_comparison_preview(
    review_service: Annotated[
        FactorValidationReviewService,
        Depends(get_factor_validation_review_service),
    ],
    validation_client: Annotated[
        FactorValidationClient,
        Depends(get_factor_validation_client),
    ],
    artifact_ledger_service: Annotated[
        ArtifactLedgerService,
        Depends(get_artifact_ledger_service),
    ],
    comparison_artifact_service: Annotated[
        FactorComparisonArtifactService,
        Depends(get_factor_comparison_artifact_service),
    ],
) -> ExternalPayloadComparisonPreviewResponse:
    artifact_reference = await artifact_ledger_service.find_latest_factor_comparison_artifact()
    artifact_read_result = await comparison_artifact_service.read_comparison_report(
        artifact_reference=artifact_reference,
    )
    if artifact_read_result.is_loaded and artifact_read_result.comparison_report is not None:
        return ExternalPayloadComparisonPreviewResponse(
            generated_at=datetime.now(timezone.utc),
            source=_resolve_preview_source(
                artifact_reference=artifact_reference,
                artifact_read_result=artifact_read_result,
            ),
            comparison_report=artifact_read_result.comparison_report,
            artifact_reference=artifact_reference,
            limitations=_build_preview_limitations(
                artifact_reference=artifact_reference,
                artifact_read_result=artifact_read_result,
            ),
        )

    request = review_service.get_external_payload_comparison_preview_request()
    comparison_report = await _compare_external_payloads(
        request=request,
        validation_client=validation_client,
    )

    return ExternalPayloadComparisonPreviewResponse(
        generated_at=datetime.now(timezone.utc),
        source=_resolve_preview_source(
            artifact_reference=artifact_reference,
            artifact_read_result=artifact_read_result,
        ),
        comparison_report=comparison_report,
        artifact_reference=artifact_reference,
        limitations=_build_preview_limitations(
            artifact_reference=artifact_reference,
            artifact_read_result=artifact_read_result,
        ),
    )


@router.post("/external-payloads/compare", response_model=FactorComparisonReport)
async def compare_external_payloads(
    request: ExternalPayloadComparisonRequest,
    validation_client: Annotated[
        FactorValidationClient,
        Depends(get_factor_validation_client),
    ],
) -> FactorComparisonReport:
    return await _compare_external_payloads(
        request=request,
        validation_client=validation_client,
    )


async def _compare_external_payloads(
    *,
    request: ExternalPayloadComparisonRequest,
    validation_client: FactorValidationClient,
) -> FactorComparisonReport:
    try:
        return await validation_client.compare_external_payloads(request=request)
    except FactorValidationClientError as error:
        if error.status_code in {
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            status.HTTP_504_GATEWAY_TIMEOUT,
        }:
            raise HTTPException(status_code=error.status_code, detail=error.message) from error
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=error.message) from error


def _resolve_preview_source(
    *,
    artifact_reference: FactorComparisonArtifactReference | None,
    artifact_read_result: FactorComparisonArtifactReadResult,
) -> str:
    if artifact_read_result.is_loaded:
        return "object_store_factor_comparison_report"
    if artifact_reference is None:
        return "quant_ops_api_mvp_external_payload_preview"
    if artifact_reference.storage_type == "preview_manifest":
        return "quant_ops_api_preview_artifact_reference"
    return "postgres_factor_comparison_artifact_reference"


def _build_preview_limitations(
    *,
    artifact_reference: FactorComparisonArtifactReference | None,
    artifact_read_result: FactorComparisonArtifactReadResult,
) -> list[str]:
    if artifact_read_result.is_loaded:
        return [
            "已通过只读 object-store adapter 读取 factor_comparison_report.v1 标准报告。",
            "当前接口只读取对象内容，不写 PostgreSQL、ClickHouse 或 MinIO。",
        ]

    if artifact_reference is not None and artifact_reference.storage_type != "preview_manifest":
        return [
            "已定位 task_artifacts 中的 factor_comparison_report.v1 产物引用。",
            f"当前未使用对象内容，原因：{artifact_read_result.message}。",
            "comparison_report 仍来自 BFF MVP 预览 payload。",
            "下一步应通过只读 object-store adapter 读取标准 comparison_report.json。",
        ]

    return [
        "当前结果来自 BFF 内置 MVP 预览 payload，不代表已读取真实研究产物。",
        "生产接入后应优先读取 task_artifacts 中的 factor_comparison_report.v1。",
    ]
