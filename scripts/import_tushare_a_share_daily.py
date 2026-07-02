from __future__ import annotations

import argparse
import base64
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import gzip
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
import urllib.error
import urllib.request


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROXY_BASE_URL = "https://tt.xiaodefa.cn"
DEFAULT_DATASET_CODE = "a_share_1d"
DEFAULT_SOURCE_NAME = "tushare_proxy"
DEFAULT_PROGRESS_DIR = REPO_ROOT / "data" / "ingestion_progress"
CLICKHOUSE_TABLE = "market_data_1d_raw"
INSERT_COLUMNS = [
    "dataset_code",
    "code",
    "date",
    "open",
    "high",
    "low",
    "close",
    "pre_close",
    "change",
    "pct_chg",
    "vol",
    "amount",
    "vwap",
    "adj_factor",
    "hfq_factor",
    "source_name",
]


@dataclass(frozen=True)
class ImportConfig:
    start_date: str
    end_date: str
    dataset_code: str
    source_name: str
    token: str
    proxy_base_url: str
    clickhouse_http_url: str
    clickhouse_database: str
    clickhouse_user: str
    clickhouse_password: str | None
    timeout_seconds: float
    sleep_seconds: float
    max_retries: int
    replace_existing: bool
    limit_trade_dates: int | None
    progress_file: Path


def load_dotenv_file(*, path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import all A-share daily bars from Tushare into ClickHouse.")
    parser.add_argument("--start-date", default="20240101", help="Inclusive start date in YYYYMMDD format.")
    parser.add_argument("--end-date", default="20260630", help="Inclusive end date in YYYYMMDD format.")
    parser.add_argument("--dataset-code", default=DEFAULT_DATASET_CODE)
    parser.add_argument("--source-name", default=DEFAULT_SOURCE_NAME)
    parser.add_argument("--proxy-base-url", default=os.environ.get("TUSHARE_PROXY_BASE_URL", DEFAULT_PROXY_BASE_URL))
    parser.add_argument("--clickhouse-http-url", default=None)
    parser.add_argument("--clickhouse-database", default=None)
    parser.add_argument("--clickhouse-user", default=None)
    parser.add_argument("--timeout-seconds", type=float, default=60)
    parser.add_argument("--sleep-seconds", type=float, default=0.15)
    parser.add_argument("--max-retries", type=int, default=3)
    parser.add_argument("--replace-existing", action="store_true")
    parser.add_argument("--limit-trade-dates", type=int, default=None)
    parser.add_argument("--progress-file", type=Path, default=None)
    return parser.parse_args()


def build_config(*, args: argparse.Namespace) -> ImportConfig:
    load_dotenv_file(path=REPO_ROOT / ".env")
    load_dotenv_file(path=REPO_ROOT / ".env.local")

    start_date = normalize_yyyymmdd(value=args.start_date, field_name="start_date")
    end_date = normalize_yyyymmdd(value=args.end_date, field_name="end_date")
    if start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date")

    progress_file = args.progress_file
    if progress_file is None:
        progress_file = DEFAULT_PROGRESS_DIR / f"tushare_a_share_daily_{start_date}_{end_date}.jsonl"

    return ImportConfig(
        start_date=start_date,
        end_date=end_date,
        dataset_code=args.dataset_code,
        source_name=args.source_name,
        token=get_required_env(name="TUSHARE_TOKEN"),
        proxy_base_url=str(args.proxy_base_url).rstrip("/") + "/",
        clickhouse_http_url=(args.clickhouse_http_url or get_required_env(name="CLICKHOUSE_HTTP_URL")).rstrip("/") + "/",
        clickhouse_database=args.clickhouse_database or os.environ.get("CLICKHOUSE_DATABASE", "quant_market"),
        clickhouse_user=args.clickhouse_user or os.environ.get("CLICKHOUSE_USER", "quant"),
        clickhouse_password=os.environ.get("CLICKHOUSE_PASSWORD") or None,
        timeout_seconds=args.timeout_seconds,
        sleep_seconds=args.sleep_seconds,
        max_retries=args.max_retries,
        replace_existing=bool(args.replace_existing),
        limit_trade_dates=args.limit_trade_dates,
        progress_file=progress_file,
    )


def normalize_yyyymmdd(*, value: str, field_name: str) -> str:
    normalized_value = value.strip().replace("-", "")
    try:
        datetime.strptime(normalized_value, "%Y%m%d")
    except ValueError as error:
        raise ValueError(f"{field_name} must use YYYYMMDD or YYYY-MM-DD format") from error
    return normalized_value


def get_required_env(*, name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"{name} is required in environment or ignored .env file")


def post_json(
    *,
    url: str,
    payload: dict[str, Any],
    timeout_seconds: float,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "content-type": "application/json",
            "accept-encoding": "gzip",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        raw_body = response.read()
        if response.headers.get("Content-Encoding") == "gzip":
            raw_body = gzip.decompress(raw_body)
        response_payload = json.loads(raw_body.decode("utf-8"))
        if isinstance(response_payload, dict):
            return response_payload
    raise RuntimeError("HTTP endpoint returned a non-object JSON response")


def query_tushare(
    *,
    config: ImportConfig,
    api_name: str,
    params: dict[str, Any],
    fields: str,
) -> list[dict[str, Any]]:
    payload = {
        "api_name": api_name,
        "token": config.token,
        "params": params,
        "fields": fields,
    }
    response_payload = run_with_retries(
        action=lambda: post_json(
            url=config.proxy_base_url,
            payload=payload,
            timeout_seconds=config.timeout_seconds,
        ),
        label=f"tushare:{api_name}",
        max_retries=config.max_retries,
    )
    return build_records_from_tushare_payload(payload=response_payload)


def build_records_from_tushare_payload(*, payload: dict[str, Any]) -> list[dict[str, Any]]:
    code = payload.get("code")
    if code not in (0, "0", None):
        message = payload.get("msg") or f"Tushare returned code {code}"
        raise RuntimeError(str(message))

    data = payload.get("data")
    if not isinstance(data, dict):
        return []

    fields = data.get("fields")
    items = data.get("items")
    if not isinstance(fields, list) or not isinstance(items, list):
        return []

    field_names = [str(field) for field in fields]
    return [
        dict(zip(field_names, item))
        for item in items
        if isinstance(item, list)
    ]


def fetch_open_trade_dates(*, config: ImportConfig) -> list[str]:
    rows = query_tushare(
        config=config,
        api_name="trade_cal",
        params={
            "exchange": "",
            "start_date": config.start_date,
            "end_date": config.end_date,
            "is_open": "1",
        },
        fields="cal_date,is_open",
    )
    trade_dates = sorted(
        str(row["cal_date"])
        for row in rows
        if str(row.get("is_open")) in {"1", "1.0", "True", "true"}
    )
    if config.limit_trade_dates is None:
        return trade_dates
    return trade_dates[: config.limit_trade_dates]


def fetch_daily_rows_by_date(*, config: ImportConfig, trade_date: str) -> list[dict[str, Any]]:
    return query_tushare(
        config=config,
        api_name="daily",
        params={"trade_date": trade_date},
        fields="ts_code,trade_date,open,high,low,close,pre_close,change,pct_chg,vol,amount",
    )


def fetch_adjustment_rows_by_date(*, config: ImportConfig, trade_date: str) -> list[dict[str, Any]]:
    return query_tushare(
        config=config,
        api_name="adj_factor",
        params={"trade_date": trade_date},
        fields="ts_code,trade_date,adj_factor",
    )


def build_adjustment_by_symbol(*, rows: list[dict[str, Any]]) -> dict[str, Decimal]:
    adjustment_by_symbol: dict[str, Decimal] = {}
    for row in rows:
        symbol = str(row.get("ts_code", "")).strip().upper()
        adjustment_factor = decimal_or_none(row.get("adj_factor"))
        if symbol and adjustment_factor is not None:
            adjustment_by_symbol[symbol] = adjustment_factor
    return adjustment_by_symbol


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None

    normalized_value = str(value).strip()
    if normalized_value.lower() in {"", "nan", "nat", "none"}:
        return None

    try:
        return Decimal(normalized_value)
    except InvalidOperation as error:
        raise ValueError(f"invalid decimal value: {normalized_value}") from error


def decimal_string_or_none(value: Any) -> str | None:
    decimal_value = decimal_or_none(value)
    if decimal_value is None:
        return None
    return format(decimal_value, "f")


def volume_shares_or_none(value: Any) -> int | None:
    volume_hands = decimal_or_none(value)
    if volume_hands is None:
        return None
    return int(volume_hands * Decimal("100"))


def calculate_vwap(*, amount_thousand_yuan: Any, volume_hands: Any) -> str | None:
    amount_value = decimal_or_none(amount_thousand_yuan)
    volume_value = decimal_or_none(volume_hands)
    if amount_value is None or volume_value in (None, Decimal("0")):
        return None
    return format((amount_value * Decimal("10")) / volume_value, "f")


def build_clickhouse_record(
    *,
    row: dict[str, Any],
    adjustment_by_symbol: dict[str, Decimal],
    config: ImportConfig,
) -> dict[str, Any]:
    symbol = str(row["ts_code"]).strip().upper()
    adjustment_factor = adjustment_by_symbol.get(symbol, Decimal("1"))
    return {
        "dataset_code": config.dataset_code,
        "code": symbol,
        "date": format_clickhouse_date(value=str(row["trade_date"])),
        "open": decimal_string_or_none(row.get("open")),
        "high": decimal_string_or_none(row.get("high")),
        "low": decimal_string_or_none(row.get("low")),
        "close": decimal_string_or_none(row.get("close")),
        "pre_close": decimal_string_or_none(row.get("pre_close")),
        "change": decimal_string_or_none(row.get("change")),
        "pct_chg": decimal_string_or_none(row.get("pct_chg")),
        "vol": volume_shares_or_none(row.get("vol")),
        "amount": decimal_string_or_none(row.get("amount")),
        "vwap": calculate_vwap(amount_thousand_yuan=row.get("amount"), volume_hands=row.get("vol")),
        "adj_factor": format(adjustment_factor, "f"),
        "hfq_factor": format(adjustment_factor, "f"),
        "source_name": config.source_name,
    }


def format_clickhouse_date(*, value: str) -> str:
    return datetime.strptime(value, "%Y%m%d").date().isoformat()


def build_clickhouse_headers(*, config: ImportConfig) -> dict[str, str]:
    headers = {"content-type": "text/plain"}
    if not config.clickhouse_password:
        return headers

    token = f"{config.clickhouse_user}:{config.clickhouse_password}".encode("utf-8")
    headers["Authorization"] = f"Basic {base64.b64encode(token).decode('ascii')}"
    return headers


def execute_clickhouse(
    *,
    config: ImportConfig,
    query: str,
    timeout_seconds: float | None = None,
) -> str:
    request = urllib.request.Request(
        config.clickhouse_http_url,
        data=query.encode("utf-8"),
        headers=build_clickhouse_headers(config=config),
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds or config.timeout_seconds) as response:
        return response.read().decode("utf-8")


def query_clickhouse_json(
    *,
    config: ImportConfig,
    query: str,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    response_text = execute_clickhouse(
        config=config,
        query=query.rstrip().rstrip(";") + " FORMAT JSON",
        timeout_seconds=timeout_seconds,
    )
    response_payload = json.loads(response_text)
    if isinstance(response_payload, dict):
        return response_payload
    raise RuntimeError("ClickHouse returned a non-object JSON response")


def existing_row_count(*, config: ImportConfig, trade_date: str) -> int:
    date_value = format_clickhouse_date(value=trade_date)
    table_name = f"{config.clickhouse_database}.{CLICKHOUSE_TABLE}"
    query = f"""
SELECT count() AS row_count
FROM {table_name}
WHERE dataset_code = {clickhouse_string(config.dataset_code)}
  AND source_name = {clickhouse_string(config.source_name)}
  AND date = toDate({clickhouse_string(date_value)})
"""
    payload = query_clickhouse_json(config=config, query=query)
    rows = payload.get("data") or []
    if not rows:
        return 0
    return int(rows[0]["row_count"])


def delete_existing_date(*, config: ImportConfig, trade_date: str) -> None:
    date_value = format_clickhouse_date(value=trade_date)
    table_name = f"{config.clickhouse_database}.{CLICKHOUSE_TABLE}"
    query = f"""
ALTER TABLE {table_name}
DELETE WHERE dataset_code = {clickhouse_string(config.dataset_code)}
  AND source_name = {clickhouse_string(config.source_name)}
  AND date = toDate({clickhouse_string(date_value)})
"""
    execute_clickhouse(config=config, query=query, timeout_seconds=300)


def insert_records(*, config: ImportConfig, records: list[dict[str, Any]]) -> None:
    if not records:
        return

    table_name = f"{config.clickhouse_database}.{CLICKHOUSE_TABLE}"
    column_list = ", ".join(INSERT_COLUMNS)
    payload_lines = [json.dumps(record, ensure_ascii=True, separators=(",", ":")) for record in records]
    query = f"INSERT INTO {table_name} ({column_list}) FORMAT JSONEachRow\n" + "\n".join(payload_lines)
    execute_clickhouse(config=config, query=query, timeout_seconds=300)


def clickhouse_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"


def append_progress(*, config: ImportConfig, event: dict[str, Any]) -> None:
    config.progress_file.parent.mkdir(parents=True, exist_ok=True)
    with config.progress_file.open("a", encoding="utf-8") as file:
        file.write(json.dumps(event, ensure_ascii=True, sort_keys=True) + "\n")


def run_import(*, config: ImportConfig) -> dict[str, Any]:
    trade_dates = fetch_open_trade_dates(config=config)
    summary = {
        "trade_dates": len(trade_dates),
        "inserted_dates": 0,
        "skipped_dates": 0,
        "empty_dates": 0,
        "inserted_rows": 0,
        "missing_adjustment_rows": 0,
    }
    print(
        "import started: "
        f"dates={len(trade_dates)} range={config.start_date}-{config.end_date} "
        f"dataset={config.dataset_code} source={config.source_name}",
        flush=True,
    )

    for index, trade_date in enumerate(trade_dates, start=1):
        existing_count = existing_row_count(config=config, trade_date=trade_date)
        if existing_count > 0 and not config.replace_existing:
            summary["skipped_dates"] += 1
            event = {
                "event": "skipped_existing",
                "trade_date": trade_date,
                "existing_rows": existing_count,
                "index": index,
                "total": len(trade_dates),
            }
            append_progress(config=config, event=event)
            print_progress(event=event)
            continue

        if existing_count > 0 and config.replace_existing:
            delete_existing_date(config=config, trade_date=trade_date)

        daily_rows = fetch_daily_rows_by_date(config=config, trade_date=trade_date)
        if not daily_rows:
            summary["empty_dates"] += 1
            event = {
                "event": "empty_daily",
                "trade_date": trade_date,
                "index": index,
                "total": len(trade_dates),
            }
            append_progress(config=config, event=event)
            print_progress(event=event)
            continue

        adjustment_rows = fetch_adjustment_rows_by_date(config=config, trade_date=trade_date)
        adjustment_by_symbol = build_adjustment_by_symbol(rows=adjustment_rows)
        records = [
            build_clickhouse_record(row=row, adjustment_by_symbol=adjustment_by_symbol, config=config)
            for row in daily_rows
        ]
        missing_adjustment_count = sum(1 for record in records if record["adj_factor"] == "1")
        insert_records(config=config, records=records)

        summary["inserted_dates"] += 1
        summary["inserted_rows"] += len(records)
        summary["missing_adjustment_rows"] += missing_adjustment_count
        event = {
            "event": "inserted",
            "trade_date": trade_date,
            "rows": len(records),
            "missing_adjustment_rows": missing_adjustment_count,
            "index": index,
            "total": len(trade_dates),
        }
        append_progress(config=config, event=event)
        print_progress(event=event)
        if config.sleep_seconds > 0:
            time.sleep(config.sleep_seconds)

    return summary


def print_progress(*, event: dict[str, Any]) -> None:
    event_name = event["event"]
    trade_date = event["trade_date"]
    index = event["index"]
    total = event["total"]
    details = " ".join(
        f"{key}={value}"
        for key, value in event.items()
        if key not in {"event", "trade_date", "index", "total"}
    )
    print(f"[{index}/{total}] {trade_date} {event_name} {details}".rstrip(), flush=True)


def run_with_retries(
    *,
    action: Any,
    label: str,
    max_retries: int,
) -> Any:
    last_error: BaseException | None = None
    for attempt in range(1, max_retries + 1):
        try:
            return action()
        except (RuntimeError, TimeoutError, urllib.error.URLError, urllib.error.HTTPError) as error:
            last_error = error
            if attempt >= max_retries:
                break
            time.sleep(min(2 ** attempt, 10))
    raise RuntimeError(f"{label} failed after {max_retries} attempts: {last_error}") from last_error


def main() -> int:
    try:
        config = build_config(args=parse_args())
        summary = run_import(config=config)
    except (RuntimeError, ValueError, urllib.error.URLError, urllib.error.HTTPError) as error:
        print(f"tushare daily import failed: {error}", file=sys.stderr)
        return 1

    print("import finished: " + json.dumps(summary, ensure_ascii=True, sort_keys=True), flush=True)
    print(f"progress file: {config.progress_file}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
