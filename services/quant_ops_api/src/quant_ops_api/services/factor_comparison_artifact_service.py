from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlparse

from pydantic import ValidationError
from quant_contracts import FactorComparisonReport

from quant_ops_api.integrations import ArtifactObjectReadError
from quant_ops_api.schemas import FactorComparisonArtifactReference


COMPARISON_REPORT_SCHEMA_VERSION = "factor_comparison_report.v1"
ComparisonArtifactReadStatus = Literal[
    "loaded",
    "artifact_reference_missing",
    "object_reader_not_configured",
    "unsupported_schema",
    "unsupported_storage",
    "missing_location",
    "read_failed",
    "invalid_payload",
]


class ArtifactObjectReader(Protocol):
    async def read_json_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass(frozen=True)
class FactorComparisonArtifactReadResult:
    status: ComparisonArtifactReadStatus
    message: str
    comparison_report: FactorComparisonReport | None = None

    @property
    def is_loaded(self) -> bool:
        return self.status == "loaded" and self.comparison_report is not None


@dataclass(frozen=True)
class FactorComparisonArtifactService:
    object_reader: ArtifactObjectReader | None = None

    async def read_comparison_report(
        self,
        *,
        artifact_reference: FactorComparisonArtifactReference | None,
    ) -> FactorComparisonArtifactReadResult:
        if artifact_reference is None:
            return _build_unloaded_result(
                status="artifact_reference_missing",
                message="factor_comparison_report.v1 artifact reference is missing",
            )
        if artifact_reference.schema_version != COMPARISON_REPORT_SCHEMA_VERSION:
            return _build_unloaded_result(
                status="unsupported_schema",
                message="artifact reference schema is not factor_comparison_report.v1",
            )
        if artifact_reference.storage_type != "minio_s3":
            return _build_unloaded_result(
                status="unsupported_storage",
                message="artifact storage type is not configured for object-store reads",
            )
        if self.object_reader is None:
            return _build_unloaded_result(
                status="object_reader_not_configured",
                message="artifact object reader is not configured",
            )

        bucket_name = _resolve_bucket_name(artifact_reference=artifact_reference)
        object_key = _resolve_object_key(artifact_reference=artifact_reference)
        if bucket_name is None or object_key is None:
            return _build_unloaded_result(
                status="missing_location",
                message="artifact reference is missing bucket_name or object_key",
            )

        try:
            payload = await self.object_reader.read_json_object(
                bucket_name=bucket_name,
                object_key=object_key,
            )
            comparison_report = FactorComparisonReport.model_validate(payload)
        except ArtifactObjectReadError as error:
            return _build_unloaded_result(status="read_failed", message=str(error))
        except ValidationError as error:
            return _build_unloaded_result(status="invalid_payload", message=str(error))

        return FactorComparisonArtifactReadResult(
            status="loaded",
            message="factor comparison report artifact loaded",
            comparison_report=comparison_report,
        )


def _build_unloaded_result(
    *,
    status: ComparisonArtifactReadStatus,
    message: str,
) -> FactorComparisonArtifactReadResult:
    return FactorComparisonArtifactReadResult(status=status, message=message)


def _resolve_bucket_name(
    *,
    artifact_reference: FactorComparisonArtifactReference,
) -> str | None:
    bucket_name = _strip_optional(value=artifact_reference.bucket_name)
    if bucket_name is not None:
        return bucket_name

    if artifact_reference.uri is None:
        return None
    parsed_uri = urlparse(artifact_reference.uri)
    if parsed_uri.scheme == "s3" and parsed_uri.netloc:
        return parsed_uri.netloc
    return None


def _resolve_object_key(
    *,
    artifact_reference: FactorComparisonArtifactReference,
) -> str | None:
    object_key = _strip_optional(value=artifact_reference.object_key)
    if object_key is not None:
        return object_key

    if artifact_reference.uri is None:
        return None
    parsed_uri = urlparse(artifact_reference.uri)
    if parsed_uri.scheme == "s3" and parsed_uri.path.strip("/"):
        return parsed_uri.path.strip("/")
    return None


def _strip_optional(*, value: str | None) -> str | None:
    if value is None:
        return None
    stripped_value = value.strip()
    if stripped_value:
        return stripped_value
    return None
