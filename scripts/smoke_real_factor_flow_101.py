from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


DEFAULT_FACTOR_LAB_BASE_URL = "http://127.0.0.1:18010"
DEFAULT_FACTOR_VALIDATION_BASE_URL = "http://127.0.0.1:18020"
DEFAULT_SYMBOLS = "000001.SZ,000651.SZ,000333.SZ,600000.SH,600519.SH"
DEFAULT_RUN_ID = "real_flow_smoke_101"
DEFAULT_EVIDENCE_GATE_ID = "validation_evidence"
DEFAULT_EVIDENCE_SUBMITTED_BY = "codex_smoke"


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


def parse_symbols(value: str) -> list[str]:
    symbols = [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
    if symbols:
        return symbols
    raise RuntimeError("REAL_FACTOR_FLOW_SYMBOLS must contain at least one symbol")


def build_factor_payload(*, symbols: list[str]) -> dict[str, Any]:
    factor_name = os.environ.get("REAL_FACTOR_FLOW_FACTOR_NAME", "momentum_1d")
    lookback_window = int(os.environ.get("REAL_FACTOR_FLOW_LOOKBACK_WINDOW", "1"))
    run_id = os.environ.get("REAL_FACTOR_FLOW_RUN_ID", DEFAULT_RUN_ID)
    return {
        "factor_name": factor_name,
        "algorithm_id": os.environ.get("REAL_FACTOR_FLOW_ALGORITHM_ID", "technical.momentum"),
        "algorithm_parameters": {"lookback_window": lookback_window},
        "symbols": symbols,
        "start": os.environ.get("REAL_FACTOR_FLOW_START", "2026-06-01"),
        "end": os.environ.get("REAL_FACTOR_FLOW_END", "2026-06-10"),
        "price_mode": os.environ.get("REAL_FACTOR_FLOW_PRICE_MODE", "qfq"),
        "batch_id": os.environ.get("REAL_FACTOR_FLOW_BATCH_ID", "qfq_20260610"),
        "lookback_window": lookback_window,
        "universe_name": os.environ.get("REAL_FACTOR_FLOW_UNIVERSE_NAME", "a_share_smoke"),
        "run_id": run_id,
        "limit": int(os.environ.get("REAL_FACTOR_FLOW_LIMIT", "10000")),
    }


def build_validation_payload(*, factor_response: dict[str, Any]) -> dict[str, Any]:
    factor_meta = factor_response["meta"]
    return {
        "factor_name": factor_meta["factor_name"],
        "factor_values": factor_response["rows"],
        "market_start": os.environ.get("REAL_FACTOR_FLOW_MARKET_START", "2026-06-01"),
        "market_end": os.environ.get("REAL_FACTOR_FLOW_MARKET_END", "2026-06-10"),
        "forward_days": int(os.environ.get("REAL_FACTOR_FLOW_FORWARD_DAYS", "1")),
        "group_count": int(os.environ.get("REAL_FACTOR_FLOW_GROUP_COUNT", "5")),
        "price_mode": factor_meta["price_mode"],
        "dataset_code": factor_meta["dataset_code"],
        "batch_id": factor_meta["batch_id"],
        "universe_name": factor_meta["universe_name"],
        "run_id": factor_meta["run_id"],
        "limit": int(os.environ.get("REAL_FACTOR_FLOW_LIMIT", "10000")),
    }


def build_evidence_payload(
    *,
    factor_response: dict[str, Any],
    validation_response: dict[str, Any],
) -> dict[str, Any]:
    factor_meta = factor_response["meta"]
    metrics = validation_response["metrics"]
    artifact = select_validation_evidence_artifact(manifest=validation_response.get("manifest", {}))
    evidence_source = artifact.get("object_key") or artifact.get("uri") or artifact["artifact_id"]
    return {
        "algorithm_id": factor_meta["algorithm_id"],
        "gate_id": os.environ.get("REAL_FACTOR_FLOW_EVIDENCE_GATE_ID", DEFAULT_EVIDENCE_GATE_ID),
        "submitted_by": os.environ.get("REAL_FACTOR_FLOW_EVIDENCE_SUBMITTED_BY", DEFAULT_EVIDENCE_SUBMITTED_BY),
        "evidence_type": "validation_report",
        "evidence_source": evidence_source,
        "summary": build_evidence_summary(metrics=metrics),
        "artifact_id": artifact.get("artifact_id"),
        "artifact_uri": artifact.get("uri"),
        "notes": [
            "source=smoke_real_factor_flow_101",
            "persistence=not_persisted",
        ],
    }


def select_validation_evidence_artifact(*, manifest: dict[str, Any]) -> dict[str, Any]:
    artifacts = manifest.get("artifacts", [])
    if not artifacts:
        raise RuntimeError("validation manifest did not include evidence artifacts")

    preferred_suffixes = ("comparison_report.json", "validation_report.json", "score_card.json")
    for suffix in preferred_suffixes:
        for artifact in artifacts:
            object_key = artifact.get("object_key") or ""
            if object_key.endswith(suffix):
                return artifact

    return artifacts[0]


def build_evidence_summary(*, metrics: dict[str, Any]) -> str:
    return (
        f"{metrics['factor_name']} validation smoke on 101 data: "
        f"effective_sample_count={metrics.get('effective_sample_count')}, "
        f"rank_ic_mean={metrics.get('rank_ic_mean')}, "
        f"ic_ir={metrics.get('ic_ir')}, "
        f"group_return_spread_mean={metrics.get('group_return_spread_mean')}."
    )


def run_smoke_test(*, factor_lab_base_url: str, factor_validation_base_url: str) -> list[str]:
    results: list[str] = []
    symbols = parse_symbols(os.environ.get("REAL_FACTOR_FLOW_SYMBOLS", DEFAULT_SYMBOLS))

    factor_response = request_json(
        base_url=factor_lab_base_url,
        path="/api/v1/factors/calculate",
        method="POST",
        payload=build_factor_payload(symbols=symbols),
        timeout_seconds=60,
    )
    factor_rows = factor_response.get("rows", [])
    non_empty_factor_rows = [row for row in factor_rows if row.get("factor_value") is not None]
    assert_condition(len(factor_rows) > 0, "factor calculation returned no rows")
    assert_condition(len(non_empty_factor_rows) > 0, "factor calculation returned no non-empty values")
    results.append(f"factor calculation ok: rows={len(factor_rows)}, non_empty={len(non_empty_factor_rows)}")

    validation_response = request_json(
        base_url=factor_validation_base_url,
        path="/api/v1/factors/validate",
        method="POST",
        payload=build_validation_payload(factor_response=factor_response),
        timeout_seconds=60,
    )
    metrics = validation_response.get("metrics", {})
    effective_sample_count = int(metrics.get("effective_sample_count", 0))
    assert_condition(effective_sample_count > 0, "factor validation returned no effective samples")
    results.append(
        "factor validation ok: "
        f"effective_sample_count={effective_sample_count}, "
        f"rank_ic_mean={metrics.get('rank_ic_mean')}, "
        f"ic_ir={metrics.get('ic_ir')}"
    )

    artifacts = validation_response.get("manifest", {}).get("artifacts", [])
    assert_condition(len(artifacts) >= 6, "validation manifest did not include all expected artifacts")
    results.append(f"validation manifest ok: artifacts={len(artifacts)}")

    evidence_response = request_json(
        base_url=factor_lab_base_url,
        path="/api/v1/algorithms/review-gates/evidence/preview",
        method="POST",
        payload=build_evidence_payload(
            factor_response=factor_response,
            validation_response=validation_response,
        ),
        timeout_seconds=30,
    )
    evidence_record = evidence_response.get("record", {})
    assert_condition(
        evidence_response.get("persistence_status") == "not_persisted",
        "evidence preview should not persist records in smoke mode",
    )
    assert_condition(
        evidence_record.get("gate_id") == os.environ.get("REAL_FACTOR_FLOW_EVIDENCE_GATE_ID", DEFAULT_EVIDENCE_GATE_ID),
        "evidence preview returned an unexpected gate_id",
    )
    results.append(
        "evidence preview ok: "
        f"algorithm_id={evidence_record.get('algorithm_id')}, "
        f"gate_id={evidence_record.get('gate_id')}, "
        f"status={evidence_record.get('evidence_status')}"
    )
    return results


def main() -> int:
    factor_lab_base_url = os.environ.get("QUANT_FACTOR_LAB_BASE_URL", DEFAULT_FACTOR_LAB_BASE_URL)
    factor_validation_base_url = os.environ.get(
        "QUANT_FACTOR_VALIDATION_BASE_URL",
        DEFAULT_FACTOR_VALIDATION_BASE_URL,
    )

    try:
        results = run_smoke_test(
            factor_lab_base_url=factor_lab_base_url,
            factor_validation_base_url=factor_validation_base_url,
        )
    except RuntimeError as error:
        print(f"real factor flow smoke failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
