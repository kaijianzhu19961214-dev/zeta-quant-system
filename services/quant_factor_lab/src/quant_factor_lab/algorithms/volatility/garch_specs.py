from quant_contracts import (
    AlgorithmCapability,
    AlgorithmParameterSpec,
    AlgorithmSpec,
    AssetClass,
    FactorFamily,
    FactorMode,
    Timeframe,
)
from quant_factor_lab.algorithms.review_gates import build_planned_volatility_review_gates


def build_planned_garch_algorithm_specs() -> list[AlgorithmSpec]:
    return [
        _build_garch_spec(
            algorithm_id="volatility.egarch",
            display_name="EGARCH volatility model",
            description="Models asymmetric log conditional variance and leverage effects.",
            tags=["volatility", "garch", "leverage_effect", "time_series"],
            limitations=[
                "First implementation should use standardized return input and avoid same-day tradability leakage.",
                "Requires fitting diagnostics before the output can be used as a production factor.",
            ],
        ),
        _build_garch_spec(
            algorithm_id="volatility.gjr_garch",
            display_name="GJR-GARCH volatility model",
            description="Models asymmetric volatility response with a negative-shock indicator term.",
            tags=["volatility", "garch", "gjr_garch", "time_series"],
            limitations=[
                "Leverage parameter significance must be reviewed before accepting the factor.",
                "Requires enough history per symbol or contract before fitting.",
            ],
        ),
        _build_garch_spec(
            algorithm_id="volatility.aparch",
            display_name="APARCH volatility model",
            description="Models asymmetric power ARCH dynamics with configurable volatility power.",
            tags=["volatility", "garch", "aparch", "time_series"],
            limitations=[
                "Power parameter policy must be fixed or reviewed before first production use.",
                "Model output should be compared against simpler realized-volatility baselines.",
            ],
        ),
    ]


def _build_garch_spec(
    *,
    algorithm_id: str,
    display_name: str,
    description: str,
    tags: list[str],
    limitations: list[str],
) -> AlgorithmSpec:
    return AlgorithmSpec(
        algorithm_id=algorithm_id,
        display_name=display_name,
        status="planned",
        description=description,
        source_library="arch",
        source_url="https://arch.readthedocs.io/",
        adapter_module="quant_factor_lab.algorithms.volatility",
        capability=AlgorithmCapability(
            asset_classes=[AssetClass.EQUITY, AssetClass.FUTURES],
            factor_modes=[FactorMode.TIME_SERIES],
            factor_families=[FactorFamily.PRICE_VOLUME, FactorFamily.MODEL],
            timeframes=[Timeframe.DAY_1],
            output_kinds=["volatility", "diagnostics", "factor_values"],
        ),
        parameters=[
            AlgorithmParameterSpec(
                name="p",
                value_type="integer",
                description="ARCH lag order.",
                default_value=1,
                minimum=1,
                maximum=5,
            ),
            AlgorithmParameterSpec(
                name="q",
                value_type="integer",
                description="GARCH lag order.",
                default_value=1,
                minimum=1,
                maximum=5,
            ),
            AlgorithmParameterSpec(
                name="distribution",
                value_type="string",
                description="Residual distribution assumption, e.g. normal or student_t.",
                default_value="normal",
            ),
        ],
        tags=tags,
        research_notes=[
            "Candidate algorithm family from the GARCH literature for volatility and leverage-effect factors.",
            "Adapter output should include predicted volatility, standardized residuals, and fit diagnostics.",
        ],
        limitations=limitations,
        review_gates=build_planned_volatility_review_gates(),
    )
