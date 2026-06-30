from math import isfinite
from typing import TypeAlias


ExternalMetricValue: TypeAlias = float | int | str | None


def normalize_factor_name(*, value: str) -> str:
    normalized_value = value.strip().lower()
    if (
        normalized_value
        and normalized_value.replace("_", "").isalnum()
        and normalized_value[0].isalpha()
    ):
        return normalized_value
    raise ValueError("factor_name must use lowercase letters, numbers, and underscores")


def normalize_optional_text(*, value: str | None) -> str | None:
    if value is None:
        return value

    normalized_value = value.strip()
    if normalized_value:
        return normalized_value
    raise ValueError("value must not be blank")


def normalize_text_list(*, value: list[str]) -> list[str]:
    return [item.strip() for item in value if item.strip()]


def normalize_metric_values(
    *,
    value: dict[str, ExternalMetricValue],
) -> dict[str, ExternalMetricValue]:
    normalized_values: dict[str, ExternalMetricValue] = {}
    for metric_name, metric_value in value.items():
        normalized_metric_name = metric_name.strip()
        if not normalized_metric_name:
            raise ValueError("metric_values keys must not be blank")
        normalized_values[normalized_metric_name] = metric_value
    return normalized_values


def find_optional_float(
    *,
    metric_values: dict[str, ExternalMetricValue],
    aliases: tuple[str, ...],
) -> float | None:
    value = find_metric_value(metric_values=metric_values, aliases=aliases)
    if value is None:
        return None
    return coerce_optional_float(value=value)


def find_optional_ratio(
    *,
    metric_values: dict[str, ExternalMetricValue],
    aliases: tuple[str, ...],
) -> float | None:
    value = find_optional_float(metric_values=metric_values, aliases=aliases)
    if value is None:
        return None
    if value > 1.0:
        return value / 100.0
    return value


def find_optional_int(
    *,
    metric_values: dict[str, ExternalMetricValue],
    aliases: tuple[str, ...],
) -> int | None:
    value = find_metric_value(metric_values=metric_values, aliases=aliases)
    if value is None:
        return None
    numeric_value = coerce_optional_float(value=value)
    if numeric_value is None:
        return None
    return int(numeric_value)


def find_metric_value(
    *,
    metric_values: dict[str, ExternalMetricValue],
    aliases: tuple[str, ...],
) -> ExternalMetricValue:
    lower_metric_values = {
        metric_name.lower(): metric_value
        for metric_name, metric_value in metric_values.items()
    }
    for alias in aliases:
        metric_value = lower_metric_values.get(alias.lower())
        if metric_value is not None:
            return metric_value
    return None


def coerce_optional_float(*, value: ExternalMetricValue) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("metric value must be numeric, not boolean")
    if isinstance(value, (int, float)):
        numeric_value = float(value)
    else:
        normalized_value = value.strip()
        if not normalized_value:
            return None
        if normalized_value.endswith("%"):
            numeric_value = float(normalized_value[:-1]) / 100.0
        else:
            numeric_value = float(normalized_value)

    if not isfinite(numeric_value):
        return None
    return numeric_value
