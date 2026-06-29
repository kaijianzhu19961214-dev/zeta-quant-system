from __future__ import annotations

import asyncio
from dataclasses import dataclass
from io import BytesIO
from typing import Any, BinaryIO, Protocol
from urllib.parse import urlparse

from minio import Minio

from quant_factor_validation.services.validation_artifacts import ValidationArtifactPayload
from quant_factor_validation.services.validation_persistence import StoredValidationArtifact


class MinioPutObjectClient(Protocol):
    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> Any:
        raise NotImplementedError


@dataclass(frozen=True)
class MinioValidationArtifactStore:
    client: MinioPutObjectClient
    bucket_name: str

    async def put_validation_artifact(
        self,
        *,
        payload: ValidationArtifactPayload,
    ) -> StoredValidationArtifact:
        metadata = {
            "artifact-id": payload.artifact_id,
            "schema-version": payload.schema_version,
            "sha256": payload.sha256,
        }
        result = await asyncio.to_thread(
            self.client.put_object,
            self.bucket_name,
            payload.object_key,
            BytesIO(payload.body),
            payload.size_bytes,
            content_type=payload.content_type,
            metadata=metadata,
        )
        etag = getattr(result, "etag", None)
        stored_metadata = {
            "object_store": "minio_s3",
            "schema_version": payload.schema_version,
        }
        if isinstance(etag, str) and etag:
            stored_metadata["etag"] = etag

        return StoredValidationArtifact(
            artifact_id=payload.artifact_id,
            object_key=payload.object_key,
            bucket_name=self.bucket_name,
            uri=f"s3://{self.bucket_name}/{payload.object_key}",
            file_size_bytes=payload.size_bytes,
            sha256=payload.sha256,
            content_type=payload.content_type,
            metadata=stored_metadata,
        )


def create_minio_client(
    *,
    endpoint: str,
    access_key: str,
    secret_key: str,
    secure: bool,
) -> Minio:
    return Minio(
        _normalize_minio_endpoint(endpoint=endpoint),
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def _normalize_minio_endpoint(*, endpoint: str) -> str:
    stripped_endpoint = endpoint.strip()
    parsed_endpoint = urlparse(stripped_endpoint)
    if parsed_endpoint.scheme in {"http", "https"} and parsed_endpoint.netloc:
        return parsed_endpoint.netloc

    if stripped_endpoint:
        return stripped_endpoint

    raise ValueError("object store endpoint must not be blank")
