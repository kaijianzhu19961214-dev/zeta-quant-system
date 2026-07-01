import unittest

from quant_ops_api.integrations.object_store import (
    ArtifactObjectReadError,
    MinioArtifactObjectReader,
    _normalize_minio_endpoint,
)


class FakeObjectResponse:
    def __init__(self, *, body: bytes) -> None:
        self.body = body
        self.is_closed = False
        self.is_released = False

    def read(self) -> bytes:
        return self.body

    def close(self) -> None:
        self.is_closed = True

    def release_conn(self) -> None:
        self.is_released = True


class FakeMinioClient:
    def __init__(self, *, response: FakeObjectResponse) -> None:
        self.response = response
        self.latest_bucket_name: str | None = None
        self.latest_object_name: str | None = None

    def get_object(self, bucket_name: str, object_name: str) -> FakeObjectResponse:
        self.latest_bucket_name = bucket_name
        self.latest_object_name = object_name
        return self.response


class ArtifactObjectStoreTest(unittest.IsolatedAsyncioTestCase):
    async def test_should_read_json_object_from_minio_client(self) -> None:
        response = FakeObjectResponse(body=b'{"factor_name": "momentum_20d"}')
        client = FakeMinioClient(response=response)
        reader = MinioArtifactObjectReader(client=client)

        payload = await reader.read_json_object(
            bucket_name="quant-factor-data",
            object_key="factor_validation/momentum_20d/comparison_report.json",
        )

        self.assertEqual(payload["factor_name"], "momentum_20d")
        self.assertEqual(client.latest_bucket_name, "quant-factor-data")
        self.assertTrue(response.is_closed)
        self.assertTrue(response.is_released)

    async def test_should_reject_non_object_json_root(self) -> None:
        reader = MinioArtifactObjectReader(client=FakeMinioClient(response=FakeObjectResponse(body=b"[]")))

        with self.assertRaises(ArtifactObjectReadError):
            await reader.read_json_object(
                bucket_name="quant-factor-data",
                object_key="factor_validation/momentum_20d/comparison_report.json",
            )

    def test_should_normalize_minio_endpoint(self) -> None:
        self.assertEqual(_normalize_minio_endpoint(endpoint="http://127.0.0.1:9000"), "127.0.0.1:9000")
        self.assertEqual(_normalize_minio_endpoint(endpoint=" https://minio.internal:9000 "), "minio.internal:9000")
        self.assertEqual(_normalize_minio_endpoint(endpoint="minio.internal:9000"), "minio.internal:9000")


if __name__ == "__main__":
    unittest.main()
