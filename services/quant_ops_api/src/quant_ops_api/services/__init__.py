from typing import Any


_EXPORTS = {
    "ArtifactLedgerService": (
        "quant_ops_api.services.artifact_ledger_service",
        "ArtifactLedgerService",
    ),
    "FactorValidationReviewService": (
        "quant_ops_api.services.factor_validation_review_service",
        "FactorValidationReviewService",
    ),
    "FactorComparisonArtifactService": (
        "quant_ops_api.services.factor_comparison_artifact_service",
        "FactorComparisonArtifactService",
    ),
    "OverviewService": (
        "quant_ops_api.services.overview_service",
        "OverviewService",
    ),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    if name not in _EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _EXPORTS[name]
    module = __import__(module_name, fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
