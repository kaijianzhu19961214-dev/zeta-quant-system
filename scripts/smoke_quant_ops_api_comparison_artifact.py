from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:18030"
DEFAULT_EXPECTED_ARTIFACT_READ_STATUS = "artifact_loaded"
VALID_ARTIFACT_READ_STATUSES = {"artifact_loaded", "preview_fallback"}


def request_json(
    *,
    base_url: str,
    path: str,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        headers={"Accept": "application/json"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GET {path} failed with HTTP {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"GET {path} failed: {error}") from error

    if isinstance(payload, dict):
        return payload
    raise RuntimeError(f"GET {path} returned non-object JSON")


def run_smoke_test(
    *,
    base_url: str,
    expected_artifact_read_status: str,
) -> list[str]:
    if expected_artifact_read_status not in VALID_ARTIFACT_READ_STATUSES:
        raise RuntimeError(
            "expected artifact read status must be artifact_loaded or preview_fallback"
        )

    results: list[str] = []
    health = request_json(base_url=base_url, path="/health")
    assert_condition(health.get("status") == "ok", "health endpoint did not return ok")
    results.append("health ok")

    preview = request_json(
        base_url=base_url,
        path="/api/v1/factor-validation/external-payloads/preview",
    )
    artifact_read_status = _read_required_str(payload=preview, key="artifact_read_status")
    artifact_read_reason = _read_optional_str(payload=preview, key="artifact_read_reason")
    source = _read_required_str(payload=preview, key="source")
    comparison_report = _read_required_object(payload=preview, key="comparison_report")
    factor_name = _read_required_str(payload=comparison_report, key="factor_name")

    assert_condition(
        artifact_read_status == expected_artifact_read_status,
        (
            "artifact read status mismatch: "
            f"expected={expected_artifact_read_status}, actual={artifact_read_status}, "
            f"reason={artifact_read_reason or 'none'}"
        ),
    )

    artifact_reference = preview.get("artifact_reference")
    if expected_artifact_read_status == "artifact_loaded":
        assert_condition(
            isinstance(artifact_reference, dict),
            "artifact_loaded response must include artifact_reference",
        )
        artifact_id = _read_required_str(payload=artifact_reference, key="artifact_id")
        results.append(f"artifact loaded ok: artifact_id={artifact_id}")
    else:
        results.append(f"preview fallback ok: reason={artifact_read_reason or 'none'}")

    results.append(f"comparison report ok: source={source}, factor_name={factor_name}")
    return results


def assert_condition(condition: bool, message: str) -> None:
    if condition:
        return
    raise RuntimeError(message)


def _read_required_object(*, payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, dict):
        return value
    raise RuntimeError(f"response missing object field: {key}")


def _read_required_str(*, payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    raise RuntimeError(f"response missing string field: {key}")


def _read_optional_str(*, payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value:
        return value
    return None


def main() -> int:
    base_url = os.environ.get("QUANT_OPS_API_BASE_URL", DEFAULT_BASE_URL)
    expected_artifact_read_status = os.environ.get(
        "QUANT_OPS_EXPECTED_ARTIFACT_READ_STATUS",
        DEFAULT_EXPECTED_ARTIFACT_READ_STATUS,
    )

    try:
        results = run_smoke_test(
            base_url=base_url,
            expected_artifact_read_status=expected_artifact_read_status,
        )
    except RuntimeError as error:
        print(f"smoke failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
