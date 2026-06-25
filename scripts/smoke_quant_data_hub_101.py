from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE_URL = "http://127.0.0.1:18000"


def request_json(
    *,
    base_url: str,
    path: str,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
    timeout_seconds: int = 30,
) -> dict[str, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=body,
        headers=headers,
        method=method,
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed with HTTP {error.code}: {error_body}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"{method} {path} failed: {error}") from error


def assert_condition(condition: bool, message: str) -> None:
    if condition:
        return
    raise RuntimeError(message)


def run_smoke_test(*, base_url: str) -> list[str]:
    results: list[str] = []

    health = request_json(base_url=base_url, path="/health")
    assert_condition(health.get("status") == "ok", "health endpoint did not return ok")
    results.append("health ok")

    batches = request_json(base_url=base_url, path="/api/v1/adjustments/qfq-batches?limit=3")
    batch_count = int(batches.get("row_count", 0))
    assert_condition(batch_count >= 1, "qfq batch query returned no rows")
    results.append(f"qfq batches ok: {batch_count}")

    raw_bars = request_json(
        base_url=base_url,
        path="/api/v1/market-bars/query",
        method="POST",
        payload={
            "timeframe": "1d",
            "symbols": ["000001.SZ"],
            "start": "2026-01-05",
            "end": "2026-01-09",
            "price_mode": "raw",
            "fields": [
                "symbol",
                "trade_date",
                "open_price",
                "high_price",
                "low_price",
                "close_price",
                "volume",
                "turnover",
            ],
            "limit": 3,
        },
    )
    raw_count = int(raw_bars.get("meta", {}).get("row_count", 0))
    assert_condition(raw_count >= 1, "raw 1d market bar query returned no rows")
    results.append(f"raw 1d bars ok: {raw_count}")

    qfq_bars = request_json(
        base_url=base_url,
        path="/api/v1/market-bars/query",
        method="POST",
        payload={
            "timeframe": "1d",
            "symbols": ["000001.SZ"],
            "start": "2026-03-13",
            "end": "2026-03-13",
            "price_mode": "qfq",
            "batch_id": "qfq_20260313",
            "fields": [
                "symbol",
                "trade_date",
                "close_price",
                "volume",
                "turnover",
                "adjustment_factor",
            ],
            "limit": 3,
        },
    )
    qfq_count = int(qfq_bars.get("meta", {}).get("row_count", 0))
    assert_condition(qfq_count >= 1, "qfq 1d market bar query returned no rows")
    results.append(f"qfq 1d bars ok: {qfq_count}")

    return results


def main() -> int:
    base_url = os.environ.get("QUANT_DATA_HUB_BASE_URL", DEFAULT_BASE_URL)
    try:
        results = run_smoke_test(base_url=base_url)
    except RuntimeError as error:
        print(f"smoke failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
