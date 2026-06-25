from enum import StrEnum


class ArtifactType(StrEnum):
    RAW_FILE = "raw_file"
    MARKET_DATA = "market_data"
    FACTOR_OUTPUT = "factor_output"
    VALIDATION_REPORT = "validation_report"
    METRICS_TABLE = "metrics_table"
    FIGURE = "figure"
    OTHER = "other"

