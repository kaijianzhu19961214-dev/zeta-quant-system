import re
from datetime import date, datetime, time

from quant_contracts import (
    MarketBar,
    MarketBarsMeta,
    MarketBarsQuery,
    MarketBarsResponse,
    PriceMode,
    QfqBatch,
    Timeframe,
)
from quant_data_hub.integrations.clickhouse import ClickHouseReader
from quant_data_hub.schemas.adjustment import QfqBatchListResponse
from quant_data_hub.schemas.source_coverage import (
    MarketDataSourceCoverageItem,
    MarketDataSourceCoverageResponse,
)

safe_value_pattern = re.compile(r"^[A-Za-z0-9_.:-]+$")
identifier_pattern = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


timeframe_config = {
    Timeframe.MINUTE_1: {
        "raw_table": "market_data_1m_raw",
        "qfq_table": "market_data_1m_qfq_cache",
        "hfq_table": "v_market_data_1m_hfq",
        "time_column": "trade_time",
        "is_intraday": True,
    },
    Timeframe.MINUTE_5: {
        "raw_table": "market_data_5m_raw",
        "qfq_table": "market_data_5m_qfq_cache",
        "hfq_table": "v_market_data_5m_hfq",
        "time_column": "trade_time",
        "is_intraday": True,
    },
    Timeframe.DAY_1: {
        "raw_table": "market_data_1d_raw",
        "qfq_table": "market_data_1d_qfq_cache",
        "hfq_table": "v_market_data_1d_hfq",
        "time_column": "date",
        "is_intraday": False,
    },
}

raw_field_mapping = {
    "symbol": "r.code",
    "trade_date": "r.date",
    "trade_time": "r.trade_time",
    "open_price": "r.open",
    "high_price": "r.high",
    "low_price": "r.low",
    "close_price": "r.close",
    "pre_close_price": "r.pre_close",
    "change_value": "r.change",
    "pct_change": "r.pct_chg",
    "volume": "r.vol",
    "turnover": "r.amount",
    "vwap": "r.vwap",
    "adjustment_factor": "r.adj_factor",
    "source_name": "r.source_name",
    "created_at": "r.created_at",
}

qfq_field_mapping = {
    "symbol": "q.code",
    "trade_date": "q.date",
    "trade_time": "q.trade_time",
    "open_price": "q.qfq_open",
    "high_price": "q.qfq_high",
    "low_price": "q.qfq_low",
    "close_price": "q.qfq_close",
    "pre_close_price": "q.qfq_pre_close",
    "change_value": "q.qfq_change",
    "pct_change": "r.pct_chg",
    "volume": "r.vol",
    "turnover": "r.amount",
    "vwap": "q.qfq_vwap",
    "adjustment_factor": "q.qfq_factor",
    "source_name": "r.source_name",
}

hfq_field_mapping = {
    "symbol": "h.code",
    "trade_date": "h.date",
    "trade_time": "h.trade_time",
    "open_price": "h.hfq_open",
    "high_price": "h.hfq_high",
    "low_price": "h.hfq_low",
    "close_price": "h.hfq_close",
    "pre_close_price": "h.hfq_pre_close",
    "change_value": "h.hfq_change",
    "pct_change": "h.pct_chg",
    "volume": "h.vol",
    "turnover": "h.amount",
    "vwap": "h.hfq_vwap",
    "adjustment_factor": "h.hfq_factor",
    "source_name": "h.source_name",
    "created_at": "h.created_at",
}

default_intraday_fields = [
    "symbol",
    "trade_time",
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
    "turnover",
    "adjustment_factor",
]

default_daily_fields = [
    "symbol",
    "trade_date",
    "open_price",
    "high_price",
    "low_price",
    "close_price",
    "volume",
    "turnover",
    "vwap",
    "adjustment_factor",
]

default_fields = {
    (Timeframe.MINUTE_1, PriceMode.RAW): default_intraday_fields,
    (Timeframe.MINUTE_5, PriceMode.RAW): default_intraday_fields,
    (Timeframe.DAY_1, PriceMode.RAW): default_daily_fields,
    (Timeframe.MINUTE_1, PriceMode.QFQ): default_intraday_fields,
    (Timeframe.MINUTE_5, PriceMode.QFQ): default_intraday_fields,
    (Timeframe.DAY_1, PriceMode.QFQ): default_daily_fields,
    (Timeframe.MINUTE_1, PriceMode.HFQ): default_intraday_fields,
    (Timeframe.MINUTE_5, PriceMode.HFQ): default_intraday_fields,
    (Timeframe.DAY_1, PriceMode.HFQ): default_daily_fields,
}

default_dataset_codes = {
    Timeframe.MINUTE_1: "a_share_1m",
    Timeframe.MINUTE_5: "a_share_5m",
    Timeframe.DAY_1: "a_share_1d",
}


def validate_identifier(value: str) -> str:
    if identifier_pattern.fullmatch(value):
        return value
    raise ValueError(f"Invalid ClickHouse identifier: {value}")


def format_table_name(*, database: str, table_name: str) -> str:
    return f"{validate_identifier(database)}.{validate_identifier(table_name)}"


def quote_sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def validate_safe_value(value: str, *, field_name: str) -> str:
    if safe_value_pattern.fullmatch(value):
        return value
    raise ValueError(f"{field_name} contains unsupported characters")


def normalize_datetime_bound(value: date | datetime | str, *, is_end: bool) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.max if is_end else time.min).replace(microsecond=0)

    normalized_value = value.strip().replace("T", " ")
    if len(normalized_value) == 10:
        parsed_date = date.fromisoformat(normalized_value)
        return datetime.combine(parsed_date, time.max if is_end else time.min).replace(microsecond=0)

    return datetime.fromisoformat(normalized_value)


def normalize_date_bound(value: date | datetime | str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value.strip()[:10])


def build_time_condition(
    *,
    timeframe: Timeframe,
    start: date | datetime | str,
    end: date | datetime | str,
    alias: str,
) -> str:
    config = timeframe_config[timeframe]
    column_name = config["time_column"]
    if not config["is_intraday"]:
        start_date = quote_sql_string(normalize_date_bound(start).isoformat())
        end_date = quote_sql_string(normalize_date_bound(end).isoformat())
        return (
            f"{alias}.{column_name} >= toDate({start_date}) "
            f"AND {alias}.{column_name} <= toDate({end_date})"
        )

    start_value = quote_sql_string(
        normalize_datetime_bound(start, is_end=False).strftime("%Y-%m-%d %H:%M:%S")
    )
    end_value = quote_sql_string(
        normalize_datetime_bound(end, is_end=True).strftime("%Y-%m-%d %H:%M:%S")
    )
    return (
        f"{alias}.{column_name} >= toDateTime64({start_value}, 0, 'Asia/Shanghai') "
        f"AND {alias}.{column_name} <= toDateTime64({end_value}, 0, 'Asia/Shanghai')"
    )


def build_select_clause(*, fields: list[str], field_mapping: dict[str, str], timeframe: Timeframe) -> str:
    select_parts: list[str] = []
    for field_name in fields:
        if field_name == "trade_time" and timeframe == Timeframe.DAY_1:
            raise ValueError("trade_time is not available for timeframe=1d")
        if field_name == "vwap" and timeframe != Timeframe.DAY_1:
            raise ValueError("vwap is only available for timeframe=1d")

        expression = field_mapping.get(field_name)
        if expression is None:
            raise ValueError(f"Unsupported field: {field_name}")
        select_parts.append(f"{expression} AS {field_name}")

    return ",\n    ".join(select_parts)


def get_field_mapping(price_mode: PriceMode) -> dict[str, str]:
    if price_mode == PriceMode.RAW:
        return raw_field_mapping
    if price_mode == PriceMode.QFQ:
        return qfq_field_mapping
    return hfq_field_mapping


def get_query_alias(price_mode: PriceMode) -> str:
    if price_mode == PriceMode.RAW:
        return "r"
    if price_mode == PriceMode.QFQ:
        return "q"
    return "h"


def get_dataset_code(request: MarketBarsQuery) -> str:
    return request.dataset_code or default_dataset_codes[request.timeframe]


class MarketQueryService:
    def __init__(self, *, reader: ClickHouseReader, database: str) -> None:
        self.reader = reader
        self.database = database

    async def query_bars(self, request: MarketBarsQuery) -> MarketBarsResponse:
        query = self.build_bars_query(request)
        payload = await self.reader.query_json(query, timeout_seconds=120)
        rows = payload.get("data", [])
        dataset_code = get_dataset_code(request)
        qfq_base_date = await self.get_qfq_base_date(request=request)
        return MarketBarsResponse(
            meta=MarketBarsMeta(
                timeframe=request.timeframe,
                price_mode=request.price_mode,
                dataset_code=dataset_code,
                batch_id=request.batch_id,
                qfq_base_date=qfq_base_date,
                row_count=len(rows),
            ),
            rows=[MarketBar.model_validate(row) for row in rows],
        )

    async def get_qfq_base_date(self, *, request: MarketBarsQuery) -> date | None:
        if request.price_mode != PriceMode.QFQ:
            return None
        if not request.batch_id:
            return None

        query = f"""
SELECT
    qfq_base_date
FROM {format_table_name(database=self.database, table_name="qfq_batches")}
WHERE batch_id = {quote_sql_string(request.batch_id)}
ORDER BY created_at DESC
LIMIT 1
"""
        payload = await self.reader.query_json(query, timeout_seconds=60)
        rows = payload.get("data", [])
        if not rows:
            return None

        qfq_base_date = rows[0].get("qfq_base_date")
        if isinstance(qfq_base_date, date):
            return qfq_base_date
        if isinstance(qfq_base_date, str):
            return date.fromisoformat(qfq_base_date[:10])
        return None

    async def list_qfq_batches(self, *, limit: int = 100) -> QfqBatchListResponse:
        query = f"""
SELECT
    batch_id,
    qfq_base_date,
    status,
    description,
    created_at,
    finished_at
FROM {format_table_name(database=self.database, table_name="qfq_batches")}
ORDER BY created_at DESC
LIMIT {limit}
"""
        payload = await self.reader.query_json(query, timeout_seconds=60)
        rows = payload.get("data", [])
        return QfqBatchListResponse(
            row_count=len(rows),
            batches=[QfqBatch.model_validate(row) for row in rows],
        )

    async def list_source_coverage(self, *, limit: int = 100) -> MarketDataSourceCoverageResponse:
        query = self.build_source_coverage_query(limit=limit)
        payload = await self.reader.query_json(query, timeout_seconds=120)
        rows = payload.get("data", [])
        coverage = [MarketDataSourceCoverageItem.model_validate(row) for row in rows]
        return MarketDataSourceCoverageResponse(row_count=len(coverage), coverage=coverage)

    def build_source_coverage_query(self, *, limit: int = 100) -> str:
        normalized_limit = max(1, min(limit, 1000))
        union_queries = [
            self.build_source_coverage_select(
                timeframe=Timeframe.DAY_1,
                table_name=timeframe_config[Timeframe.DAY_1]["raw_table"],
                duplicate_key_column="date",
            ),
            self.build_source_coverage_select(
                timeframe=Timeframe.MINUTE_1,
                table_name=timeframe_config[Timeframe.MINUTE_1]["raw_table"],
                duplicate_key_column="trade_time",
            ),
            self.build_source_coverage_select(
                timeframe=Timeframe.MINUTE_5,
                table_name=timeframe_config[Timeframe.MINUTE_5]["raw_table"],
                duplicate_key_column="trade_time",
            ),
        ]
        union_sql = "\nUNION ALL\n".join(union_queries)
        return f"""
SELECT *
FROM (
{union_sql}
)
ORDER BY row_count DESC, timeframe, dataset_code, source_name
LIMIT {normalized_limit}
"""

    def build_source_coverage_select(
        self,
        *,
        timeframe: Timeframe,
        table_name: str,
        duplicate_key_column: str,
    ) -> str:
        formatted_table_name = format_table_name(database=self.database, table_name=table_name)
        return f"""
SELECT
    {quote_sql_string(timeframe.value)} AS timeframe,
    {quote_sql_string(table_name)} AS storage_object,
    dataset_code,
    source_name,
    count() AS row_count,
    uniqExact(code) AS symbol_count,
    uniqExact(date) AS trading_day_count,
    min(date) AS min_date,
    max(date) AS max_date,
    count() - uniqExact(tuple(dataset_code, code, {duplicate_key_column})) AS duplicate_key_rows
FROM {formatted_table_name}
GROUP BY dataset_code, source_name
"""

    def build_bars_query(self, request: MarketBarsQuery) -> str:
        dataset_code = get_dataset_code(request)
        validate_safe_value(dataset_code, field_name="dataset_code")
        for symbol in request.symbols:
            validate_safe_value(symbol, field_name="symbol")
        if request.batch_id is not None:
            validate_safe_value(request.batch_id, field_name="batch_id")

        fields = request.fields or default_fields[(request.timeframe, request.price_mode)]
        field_mapping = get_field_mapping(request.price_mode)
        select_clause = build_select_clause(fields=fields, field_mapping=field_mapping, timeframe=request.timeframe)
        alias = get_query_alias(request.price_mode)
        conditions = [
            f"{alias}.dataset_code = {quote_sql_string(dataset_code)}",
            f"{alias}.code IN ({', '.join(quote_sql_string(symbol) for symbol in request.symbols)})",
            build_time_condition(timeframe=request.timeframe, start=request.start, end=request.end, alias=alias),
        ]
        if request.price_mode == PriceMode.QFQ:
            conditions.append(f"q.batch_id = {quote_sql_string(request.batch_id or '')}")

        return "\n".join(
            [
                f"SELECT\n    {select_clause}",
                self.build_from_clause(request),
                "WHERE " + "\n  AND ".join(conditions),
                f"ORDER BY {alias}.code, {alias}.{timeframe_config[request.timeframe]['time_column']}",
                f"LIMIT {request.limit}",
            ]
        )

    def build_from_clause(self, request: MarketBarsQuery) -> str:
        config = timeframe_config[request.timeframe]
        if request.price_mode == PriceMode.RAW:
            table_name = format_table_name(database=self.database, table_name=config["raw_table"])
            return f"FROM {table_name} AS r"

        if request.price_mode == PriceMode.HFQ:
            table_name = format_table_name(database=self.database, table_name=config["hfq_table"])
            return f"FROM {table_name} AS h"

        qfq_table_name = format_table_name(database=self.database, table_name=config["qfq_table"])
        raw_table_name = format_table_name(database=self.database, table_name=config["raw_table"])
        time_column = config["time_column"]
        return f"""
FROM {qfq_table_name} AS q
ANY LEFT JOIN {raw_table_name} AS r
    ON q.dataset_code = r.dataset_code
   AND q.code = r.code
   AND q.{time_column} = r.{time_column}
"""
