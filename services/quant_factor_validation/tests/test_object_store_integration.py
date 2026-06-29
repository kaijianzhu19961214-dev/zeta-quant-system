from dataclasses import dataclass
from typing import BinaryIO
import unittest

from quant_factor_validation.integrations.object_store import (
    MinioValidationArtifactStore,
    _normalize_minio_endpoint,
)
from quant_factor_validation.services import ValidationArtifactPayload


class FakePutObjectResult:
    def __init__(self, *, etag: str) -> None:
        self.etag = etag


@dataclass(frozen=True)
class PutObjectCall:
    bucket_name: str
    object_name: str
    body: bytes
    length: int
    content_type: str
    metadata: dict[str, str] | None


class FakeMinioClient:
    def __init__(self) -> None:
        self.calls: list[PutObjectCall] = []

    def put_object(
        self,
        bucket_name: str,
        object_name: str,
        data: BinaryIO,
        length: int,
        content_type: str = "application/octet-stream",
        metadata: dict[str, str] | None = None,
    ) -> FakePutObjectResult:
        self.calls.append(
            PutObjectCall(
                bucket_name=bucket_name,
                object_name=object_name,
                body=data.read(),
                length=length,
                content_type=content_type,
                metadata=metadata,
            )
        )
        return FakePutObjectResult(etag="etag-123")


class ObjectStoreIntegrationTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_put_validation_artifact_to_minio_client(self) -> None:
        client = FakeMinioClient()
        store = MinioValidationArtifactStore(
            client=client,
            bucket_name="quant-factor-data",
        )
        payload = ValidationArtifactPayload(
            artifact_id="artifact_1",
            object_key="factor_validation/momentum_1d/run_1/metrics.json",
            schema_version="factor_validation_metrics.v1",
            content_type="application/json",
            body=b'{"ok":true}',
            sha256="sha-123",
            size_bytes=11,
        )

        stored_artifact = await store.put_validation_artifact(payload=payload)

        self.assertEqual(len(client.calls), 1)
        call = client.calls[0]
        self.assertIsNotNone(call.metadata)
        metadata = call.metadata or {}
        self.assertEqual(call.bucket_name, "quant-factor-data")
        self.assertEqual(call.object_name, payload.object_key)
        self.assertEqual(call.body, payload.body)
        self.assertEqual(call.length, payload.size_bytes)
        self.assertEqual(call.content_type, "application/json")
        self.assertEqual(metadata["artifact-id"], "artifact_1")
        self.assertEqual(metadata["schema-version"], payload.schema_version)
        self.assertEqual(stored_artifact.bucket_name, "quant-factor-data")
        self.assertEqual(stored_artifact.uri, f"s3://quant-factor-data/{payload.object_key}")
        self.assertEqual(stored_artifact.metadata["etag"], "etag-123")
        self.assertEqual(stored_artifact.metadata["object_store"], "minio_s3")

    def test_should_normalize_http_endpoint_for_minio_sdk(self) -> None:
        self.assertEqual(
            _normalize_minio_endpoint(endpoint="http://127.0.0.1:9000"),
            "127.0.0.1:9000",
        )
        self.assertEqual(
            _normalize_minio_endpoint(endpoint=" https://minio.internal:9000 "),
            "minio.internal:9000",
        )
        self.assertEqual(
            _normalize_minio_endpoint(endpoint="minio.internal:9000"),
            "minio.internal:9000",
        )

    def test_should_reject_blank_endpoint(self) -> None:
        with self.assertRaisesRegex(ValueError, "endpoint"):
            _normalize_minio_endpoint(endpoint=" ")


if __name__ == "__main__":
    unittest.main()
