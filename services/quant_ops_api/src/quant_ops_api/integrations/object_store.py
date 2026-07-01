from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse

from minio import Minio
from minio.error import S3Error


class ArtifactObjectReadError(RuntimeError):
    pass


class MinioGetObjectResponse(Protocol):
    def read(self) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError

    def release_conn(self) -> None:
        raise NotImplementedError


class MinioGetObjectClient(Protocol):
    def get_object(self, bucket_name: str, object_name: str) -> MinioGetObjectResponse:
        raise NotImplementedError


@dataclass(frozen=True)
class MinioArtifactObjectReader:
    client: MinioGetObjectClient

    async def read_json_object(
        self,
        *,
        bucket_name: str,
        object_key: str,
    ) -> dict[str, Any]:
        body = await asyncio.to_thread(
            _read_object_bytes,
            client=self.client,
            bucket_name=bucket_name,
            object_key=object_key,
        )
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ArtifactObjectReadError("artifact object is not valid UTF-8 JSON") from error

        if isinstance(payload, dict):
            return payload
        raise ArtifactObjectReadError("artifact object JSON root must be an object")


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


def _read_object_bytes(
    *,
    client: MinioGetObjectClient,
    bucket_name: str,
    object_key: str,
) -> bytes:
    response: MinioGetObjectResponse | None = None
    try:
        response = client.get_object(bucket_name, object_key)
        return response.read()
    except S3Error as error:
        raise ArtifactObjectReadError(f"artifact object read failed: {error.code}") from error
    except OSError as error:
        raise ArtifactObjectReadError("artifact object read failed") from error
    finally:
        if response is not None:
            response.close()
            response.release_conn()


def _normalize_minio_endpoint(*, endpoint: str) -> str:
    stripped_endpoint = endpoint.strip()
    parsed_endpoint = urlparse(stripped_endpoint)
    if parsed_endpoint.scheme in {"http", "https"} and parsed_endpoint.netloc:
        return parsed_endpoint.netloc

    if stripped_endpoint:
        return stripped_endpoint

    raise ValueError("object store endpoint must not be blank")
