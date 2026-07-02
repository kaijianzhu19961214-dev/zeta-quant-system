from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for source_path in (
    REPO_ROOT / "packages" / "quant_contracts" / "src",
    REPO_ROOT / "services" / "quant_data_hub" / "src",
    REPO_ROOT / "services" / "quant_factor_lab" / "src",
    REPO_ROOT / "services" / "quant_factor_validation" / "src",
):
    sys.path.insert(0, str(source_path))

from quant_contracts import AssetClass, FactorFamily, FactorMode
from quant_data_hub.integrations.tushare import (
    TushareDailyBarsRequest,
    TushareMarketDataClient,
)
from quant_factor_lab.factors import calculate_momentum_factor
from quant_factor_validation.metrics import (
    calculate_forward_returns,
    calculate_group_return_spread_mean,
    calculate_group_returns,
    calculate_ic_series,
    mean_optional,
    standard_deviation,
)


DEFAULT_SYMBOLS = "000001.SZ,000651.SZ,000333.SZ,600000.SH,600519.SH"
DEFAULT_START_DATE = "20260601"
DEFAULT_END_DATE = "20260610"
DEFAULT_FACTOR_NAME = "momentum_1d"
DEFAULT_RUN_ID = "tushare_factor_sample"


def assert_condition(condition: bool, message: str) -> None:
    if condition:
        return
    raise RuntimeError(message)


def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    raise RuntimeError(f"{name} is required; set it in your local shell or ignored .env file")


def parse_symbols(value: str) -> list[str]:
    symbols = [symbol.strip().upper() for symbol in value.split(",") if symbol.strip()]
    if symbols:
        return symbols
    raise RuntimeError("TUSHARE_SMOKE_SYMBOLS must contain at least one symbol")


def run_smoke_test() -> list[str]:
    token = get_required_env("TUSHARE_TOKEN")
    symbols = parse_symbols(os.environ.get("TUSHARE_SMOKE_SYMBOLS", DEFAULT_SYMBOLS))
    start_date = os.environ.get("TUSHARE_SMOKE_START_DATE", DEFAULT_START_DATE)
    end_date = os.environ.get("TUSHARE_SMOKE_END_DATE", DEFAULT_END_DATE)
    price_mode = os.environ.get("TUSHARE_SMOKE_PRICE_MODE", "qfq").strip().lower()
    factor_name = os.environ.get("TUSHARE_SMOKE_FACTOR_NAME", DEFAULT_FACTOR_NAME)
    lookback_window = int(os.environ.get("TUSHARE_SMOKE_LOOKBACK_WINDOW", "1"))
    forward_days = int(os.environ.get("TUSHARE_SMOKE_FORWARD_DAYS", "1"))
    group_count = int(os.environ.get("TUSHARE_SMOKE_GROUP_COUNT", "5"))
    run_id = os.environ.get("TUSHARE_SMOKE_RUN_ID", DEFAULT_RUN_ID)
    proxy_base_url = os.environ.get("TUSHARE_PROXY_BASE_URL")

    client = TushareMarketDataClient(token=token, proxy_base_url=proxy_base_url)
    daily_response = client.fetch_daily_bars(
        request=TushareDailyBarsRequest(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
            price_mode=price_mode,
        )
    )
    bars = daily_response.bars
    assert_condition(len(bars) > 0, "Tushare daily query returned no rows")

    factor_values = calculate_momentum_factor(
        bars=bars,
        factor_name=factor_name,
        lookback_window=lookback_window,
        asset_class=AssetClass.EQUITY,
        factor_mode=FactorMode.CROSS_SECTIONAL,
        factor_family=FactorFamily.PRICE_VOLUME,
        universe_name=os.environ.get("TUSHARE_SMOKE_UNIVERSE_NAME", "tushare_smoke"),
        data_source="tushare_sdk",
        data_version=os.environ.get("TUSHARE_SMOKE_DATA_VERSION"),
        factor_version=os.environ.get("TUSHARE_SMOKE_FACTOR_VERSION", "v1"),
        run_id=run_id,
    )
    non_empty_factor_count = sum(1 for value in factor_values if value.factor_value is not None)
    assert_condition(non_empty_factor_count > 0, "momentum factor returned no non-empty values")

    forward_returns = calculate_forward_returns(bars=bars, forward_days=forward_days)
    ic_series = calculate_ic_series(factor_values=factor_values, forward_returns=forward_returns)
    group_returns = calculate_group_returns(
        factor_values=factor_values,
        forward_returns=forward_returns,
        group_count=group_count,
    )
    effective_sample_count = sum(point.sample_size for point in ic_series)
    assert_condition(effective_sample_count > 0, "IC calculation returned no effective samples")

    ic_values = [point.ic for point in ic_series]
    rank_ic_values = [point.rank_ic for point in ic_series]
    ic_mean = mean_optional(ic_values)
    ic_std = standard_deviation(ic_values)
    ic_ir = ic_mean / ic_std if ic_mean is not None and ic_std not in (None, 0) else None

    return [
        f"tushare daily bars ok: rows={len(bars)}, symbols={len(symbols)}, price_mode={price_mode}",
        f"factor calculation ok: rows={len(factor_values)}, non_empty={non_empty_factor_count}",
        (
            "validation metrics ok: "
            f"effective_sample_count={effective_sample_count}, "
            f"ic_mean={ic_mean}, "
            f"rank_ic_mean={mean_optional(rank_ic_values)}, "
            f"ic_ir={ic_ir}, "
            f"group_return_spread_mean={calculate_group_return_spread_mean(group_returns=group_returns)}"
        ),
    ]


def main() -> int:
    try:
        results = run_smoke_test()
    except (RuntimeError, ValueError) as error:
        print(f"tushare factor smoke failed: {error}", file=sys.stderr)
        return 1

    for result in results:
        print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
