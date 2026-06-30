from typing import Any


_EXPORTS = {
    "AlphalensMetricSummary": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "AlphalensMetricSummary",
    ),
    "AlphalensMetricPayload": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "AlphalensMetricPayload",
    ),
    "FactorValidationService": (
        "quant_factor_validation.services.factor_validation_service",
        "FactorValidationService",
    ),
    "QlibMetricPayload": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "QlibMetricPayload",
    ),
    "QlibMetricSummary": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "QlibMetricSummary",
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
    "VectorbtMetricPayload": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "VectorbtMetricPayload",
    ),
    "VectorbtMetricSummary": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "VectorbtMetricSummary",
    ),
    "build_factor_comparison_report": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_comparison_report",
    ),
    "build_alphalens_external_summary": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "build_alphalens_external_summary",
    ),
    "build_alphalens_metric_summary_from_payload": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "build_alphalens_metric_summary_from_payload",
    ),
    "build_alphalens_factor_evaluation_result": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "build_alphalens_factor_evaluation_result",
    ),
    "build_external_factor_evaluation_result": (
        "quant_factor_validation.services.external_evaluation_adapter",
        "build_external_factor_evaluation_result",
    ),
    "build_external_factor_validation_metric": (
        "quant_factor_validation.services.external_evaluation_adapter",
        "build_external_factor_validation_metric",
    ),
    "build_factor_evaluation_result": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_evaluation_result",
    ),
    "build_factor_score_card": (
        "quant_factor_validation.services.factor_scoring",
        "build_factor_score_card",
    ),
    "build_qlib_external_summary": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "build_qlib_external_summary",
    ),
    "build_qlib_factor_evaluation_result": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "build_qlib_factor_evaluation_result",
    ),
    "build_qlib_metric_summary_from_payload": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "build_qlib_metric_summary_from_payload",
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
    "build_vectorbt_external_summary": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "build_vectorbt_external_summary",
    ),
    "build_vectorbt_factor_evaluation_result": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "build_vectorbt_factor_evaluation_result",
    ),
    "build_vectorbt_metric_summary_from_payload": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "build_vectorbt_metric_summary_from_payload",
    ),
    "enrich_manifest_with_artifact_payloads": (
        "quant_factor_validation.services.validation_artifacts",
        "enrich_manifest_with_artifact_payloads",
    ),
    "run_alphalens_payload_evaluation": (
        "quant_factor_validation.services.alphalens_evaluation_normalizer",
        "run_alphalens_payload_evaluation",
    ),
    "run_qlib_payload_evaluation": (
        "quant_factor_validation.services.qlib_evaluation_normalizer",
        "run_qlib_payload_evaluation",
    ),
    "run_vectorbt_payload_evaluation": (
        "quant_factor_validation.services.vectorbt_evaluation_normalizer",
        "run_vectorbt_payload_evaluation",
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
