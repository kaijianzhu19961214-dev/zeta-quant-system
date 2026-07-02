from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

from pydantic import BaseModel, Field, field_validator, model_validator
from quant_contracts import MarketBar


TusharePriceMode = Literal["raw", "qfq"]


class TushareSdkUnavailableError(RuntimeError):
    """Raised when the optional Tushare SDK is not installed."""


class TushareProClient(Protocol):
    def daily(self, *, ts_code: str, start_date: str, end_date: str) -> Any:
        """Return Tushare daily bars for one symbol."""

    def adj_factor(self, *, ts_code: str, start_date: str, end_date: str) -> Any:
        """Return Tushare adjustment factors for one symbol."""


class TushareDailyBarsRequest(BaseModel):
    symbols: list[str] = Field(min_length=1, max_length=500)
    start_date: str = Field(min_length=8, max_length=8)
    end_date: str = Field(min_length=8, max_length=8)
    price_mode: TusharePriceMode = "raw"
    source_name: str = Field(default="tushare", min_length=1, max_length=128)

    @field_validator("symbols")
    @classmethod
    def normalize_symbols(cls, value: list[str]) -> list[str]:
        normalized_symbols = [symbol.strip().upper() for symbol in value if symbol.strip()]
        if normalized_symbols:
            return normalized_symbols
        raise ValueError("symbols must not be empty")

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_yyyymmdd(cls, value: str) -> str:
        normalized_value = value.strip()
        try:
            datetime.strptime(normalized_value, "%Y%m%d")
        except ValueError as error:
            raise ValueError("date must use YYYYMMDD format") from error
        return normalized_value

    @model_validator(mode="after")
    def validate_date_range(self) -> "TushareDailyBarsRequest":
        if self.start_date <= self.end_date:
            return self
        raise ValueError("start_date must be less than or equal to end_date")


class TushareDailyBarsResponse(BaseModel):
    row_count: int = Field(ge=0)
    price_mode: TusharePriceMode
    source_name: str
    bars: list[MarketBar] = Field(default_factory=list)


class TushareMarketDataClient:
    def __init__(
        self,
        *,
        token: str | None = None,
        pro_client: TushareProClient | None = None,
    ) -> None:
        if pro_client is not None:
            self.pro_client = pro_client
            return

        if not token:
            raise ValueError("token is required when pro_client is not provided")

        self.pro_client = build_tushare_pro_client(token=token)

    def fetch_daily_bars(self, *, request: TushareDailyBarsRequest) -> TushareDailyBarsResponse:
        bars: list[MarketBar] = []
        for symbol in request.symbols:
            bars.extend(self._fetch_symbol_daily_bars(symbol=symbol, request=request))

        return TushareDailyBarsResponse(
            row_count=len(bars),
            price_mode=request.price_mode,
            source_name=request.source_name,
            bars=bars,
        )

    def _fetch_symbol_daily_bars(
        self,
        *,
        symbol: str,
        request: TushareDailyBarsRequest,
    ) -> list[MarketBar]:
        daily_rows = dataframe_records(
            self.pro_client.daily(
                ts_code=symbol,
                start_date=request.start_date,
                end_date=request.end_date,
            )
        )
        adj_rows = []
        if request.price_mode == "qfq":
            adj_rows = dataframe_records(
                self.pro_client.adj_factor(
                    ts_code=symbol,
                    start_date=request.start_date,
                    end_date=request.end_date,
                )
            )
        if request.price_mode == "qfq" and not adj_rows:
            raise ValueError(f"Tushare adj_factor returned no rows for {symbol}")

        adjustment_by_date = build_adjustment_by_date(rows=adj_rows)
        latest_adjustment_factor = resolve_latest_adjustment_factor(adjustment_by_date=adjustment_by_date)

        bars: list[MarketBar] = []
        for row in sorted(daily_rows, key=lambda item: str(item["trade_date"])):
            trade_date_key = str(row["trade_date"])
            adjustment_factor = adjustment_by_date.get(trade_date_key)
            if request.price_mode == "qfq" and adjustment_factor is None:
                raise ValueError(f"Tushare adj_factor missing for {symbol} {trade_date_key}")

            price_factor = resolve_price_factor(
                price_mode=request.price_mode,
                adjustment_factor=adjustment_factor,
                latest_adjustment_factor=latest_adjustment_factor,
            )
            bars.append(
                build_market_bar_from_tushare_row(
                    row=row,
                    price_factor=price_factor,
                    adjustment_factor=adjustment_factor,
                    source_name=request.source_name,
                )
            )

        return bars


def build_tushare_pro_client(*, token: str) -> TushareProClient:
    try:
        import tushare as ts
    except ModuleNotFoundError as error:
        raise TushareSdkUnavailableError(
            "tushare SDK is not installed; install quant-data-hub[tushare] or install tushare locally"
        ) from error

    return ts.pro_api(token)


def dataframe_records(dataframe: Any) -> list[dict[str, Any]]:
    if dataframe is None:
        return []
    if getattr(dataframe, "empty", False):
        return []
    return list(dataframe.to_dict("records"))


def build_adjustment_by_date(*, rows: list[dict[str, Any]]) -> dict[str, Decimal | None]:
    return {
        str(row["trade_date"]): decimal_or_none(row.get("adj_factor"))
        for row in rows
        if row.get("trade_date") is not None
    }


def resolve_latest_adjustment_factor(
    *,
    adjustment_by_date: dict[str, Decimal | None],
) -> Decimal | None:
    valid_items = [
        (trade_date, adjustment_factor)
        for trade_date, adjustment_factor in adjustment_by_date.items()
        if adjustment_factor is not None and adjustment_factor > 0
    ]
    if not valid_items:
        return None

    return sorted(valid_items, key=lambda item: item[0])[-1][1]


def resolve_price_factor(
    *,
    price_mode: TusharePriceMode,
    adjustment_factor: Decimal | None,
    latest_adjustment_factor: Decimal | None,
) -> Decimal:
    if price_mode == "raw":
        return Decimal("1")
    if adjustment_factor is None or latest_adjustment_factor is None:
        return Decimal("1")
    if latest_adjustment_factor == 0:
        return Decimal("1")
    return adjustment_factor / latest_adjustment_factor


def build_market_bar_from_tushare_row(
    *,
    row: dict[str, Any],
    price_factor: Decimal,
    adjustment_factor: Decimal | None,
    source_name: str,
) -> MarketBar:
    return MarketBar(
        symbol=str(row["ts_code"]),
        trade_date=parse_trade_date(row["trade_date"]),
        open_price=adjust_price(row.get("open"), price_factor=price_factor),
        high_price=adjust_price(row.get("high"), price_factor=price_factor),
        low_price=adjust_price(row.get("low"), price_factor=price_factor),
        close_price=adjust_price(row.get("close"), price_factor=price_factor),
        pre_close_price=adjust_price(row.get("pre_close"), price_factor=price_factor),
        change_value=decimal_or_none(row.get("change")),
        pct_change=decimal_or_none(row.get("pct_chg")),
        volume=decimal_or_none(row.get("vol")),
        turnover=decimal_or_none(row.get("amount")),
        adjustment_factor=adjustment_factor,
        source_name=source_name,
    )


def parse_trade_date(value: Any) -> date:
    return datetime.strptime(str(value), "%Y%m%d").date()


def decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None

    normalized_value = str(value).strip()
    if normalized_value.lower() in {"", "nan", "nat", "none"}:
        return None

    try:
        return Decimal(normalized_value)
    except InvalidOperation as error:
        raise ValueError(f"invalid decimal value from Tushare: {normalized_value}") from error


def adjust_price(value: Any, *, price_factor: Decimal) -> Decimal | None:
    decimal_value = decimal_or_none(value)
    if decimal_value is None:
        return None
    return decimal_value * price_factor
