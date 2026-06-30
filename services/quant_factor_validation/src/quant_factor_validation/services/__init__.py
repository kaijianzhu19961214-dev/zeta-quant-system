from typing import Any


_EXPORTS = {
    "FactorValidationService": (
        "quant_factor_validation.services.factor_validation_service",
        "FactorValidationService",
    ),
    "StoredValidationArtifact": (
        "quant_factor_validation.services.validation_persistence",
        "StoredValidationArtifact",
    ),
    "ValidationArtifactPayload": (
        "quant_factor_validation.services.validation_artifacts",
        "ValidationArtifactPayload",
    ),
    "ValidationArtifactStore": (
        "quant_factor_validation.services.validation_persistence",
        "ValidationArtifactStore",
    ),
    "ValidationLedgerRepository": (
        "quant_factor_validation.services.validation_persistence",
        "ValidationLedgerRepository",
    ),
    "ValidationPersistenceError": (
        "quant_factor_validation.services.validation_persistence",
        "ValidationPersistenceError",
    ),
    "ValidationPersistenceService": (
        "quant_factor_validation.services.validation_persistence",
        "ValidationPersistenceService",
    ),
    "build_factor_comparison_report": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_comparison_report",
    ),
    "build_factor_evaluation_result": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_evaluation_result",
    ),
    "build_factor_score_card": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_score_card",
    ),
    "build_validation_artifact_payloads": (
        "quant_factor_validation.services.validation_artifacts",
        "build_validation_artifact_payloads",
    ),
    "build_validation_manifest": (
        "quant_factor_validation.services.validation_manifest",
        "build_validation_manifest",
    ),
    "build_validation_report": (
        "quant_factor_validation.services.validation_report",
        "build_validation_report",
    ),
    "enrich_manifest_with_artifact_payloads": (
        "quant_factor_validation.services.validation_artifacts",
        "enrich_manifest_with_artifact_payloads",
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
