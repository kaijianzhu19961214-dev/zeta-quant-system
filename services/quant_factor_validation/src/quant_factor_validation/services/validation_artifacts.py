from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any

from quant_contracts import (
    FactorGroupReturnPoint,
    FactorIcPoint,
    FactorValidationManifest,
    FactorValidationMetric,
    FactorValidationReport,
)


ARTIFACT_CONTENT_TYPE = "application/json"


@dataclass(frozen=True)
class ValidationArtifactPayload:
    artifact_id: str
    object_key: str
    schema_version: str
    content_type: str
    body: bytes
    sha256: str
    size_bytes: int


def build_validation_artifact_payloads(
    *,
    manifest: FactorValidationManifest,
    metrics: FactorValidationMetric,
    report: FactorValidationReport,
    ic_series: list[FactorIcPoint],
    group_returns: list[FactorGroupReturnPoint],
) -> list[ValidationArtifactPayload]:
    payload_by_schema = {
        "factor_validation_report.v1": report.model_dump(mode="json"),
        "factor_validation_metrics.v1": metrics.model_dump(mode="json"),
        "factor_ic_series.v1": [point.model_dump(mode="json") for point in ic_series],
        "factor_group_returns.v1": [point.model_dump(mode="json") for point in group_returns],
    }

    artifact_payloads: list[ValidationArtifactPayload] = []
    for artifact in manifest.artifacts:
        schema_version = _read_schema_version(metadata=artifact.metadata)
        payload = payload_by_schema.get(schema_version)
        if payload is None:
            raise ValueError(f"unsupported validation artifact schema: {schema_version}")
        if artifact.object_key is None:
            raise ValueError("artifact object_key is required for materialization")

        body = _to_json_bytes(payload)
        artifact_payloads.append(
            ValidationArtifactPayload(
                artifact_id=artifact.artifact_id,
                object_key=artifact.object_key,
                schema_version=schema_version,
                content_type=ARTIFACT_CONTENT_TYPE,
                body=body,
                sha256=sha256(body).hexdigest(),
                size_bytes=len(body),
            )
        )

    return artifact_payloads


def enrich_manifest_with_artifact_payloads(
    *,
    manifest: FactorValidationManifest,
    artifact_payloads: list[ValidationArtifactPayload],
) -> FactorValidationManifest:
    payload_by_artifact_id = {payload.artifact_id: payload for payload in artifact_payloads}
    enriched_artifacts = []

    for artifact in manifest.artifacts:
        payload = payload_by_artifact_id.get(artifact.artifact_id)
        if payload is None:
            enriched_artifacts.append(artifact)
            continue

        enriched_artifacts.append(
            artifact.model_copy(
                update={
                    "file_size_bytes": payload.size_bytes,
                    "metadata": {
                        **artifact.metadata,
                        "content_type": payload.content_type,
                        "sha256": payload.sha256,
                    },
                }
            )
        )

    return manifest.model_copy(update={"artifacts": enriched_artifacts})


def _read_schema_version(*, metadata: dict[str, Any]) -> str:
    schema_version = metadata.get("schema_version")
    if isinstance(schema_version, str) and schema_version:
        return schema_version
    raise ValueError("artifact metadata.schema_version is required")


def _to_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
