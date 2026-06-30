from enum import StrEnum


class AssetClass(StrEnum):
    EQUITY = "equity"
    FUTURES = "futures"


class FactorMode(StrEnum):
    CROSS_SECTIONAL = "cross_sectional"
    TIME_SERIES = "time_series"


class FactorFamily(StrEnum):
    PRICE_VOLUME = "price_volume"
    TERM_STRUCTURE = "term_structure"
    FUNDAMENTAL = "fundamental"
    MACRO = "macro"
    MODEL = "model"


class EvaluationEngine(StrEnum):
    INTERNAL = "internal"
    ALPHALENS = "alphalens"
    QLIB = "qlib"
    VECTORBT = "vectorbt"
    OPENSOURCE_AP = "opensource_ap"
    COMMODITY_CURVE = "commodity_curve"
