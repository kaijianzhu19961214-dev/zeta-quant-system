from pydantic import Field, model_validator

from quant_contracts import EvaluationEngine, FactorComparisonReport, FactorEvaluationResult
from quant_contracts.schemas.common import ContractModel
from quant_factor_validation.services.alphalens_evaluation_normalizer import (
    AlphalensMetricPayload,
    run_alphalens_payload_evaluation,
)
from quant_factor_validation.services.factor_scoring import build_factor_comparison_report
from quant_factor_validation.services.qlib_evaluation_normalizer import (
    QlibMetricPayload,
    run_qlib_payload_evaluation,
)
from quant_factor_validation.services.vectorbt_evaluation_normalizer import (
    VectorbtMetricPayload,
    run_vectorbt_payload_evaluation,
)


class ExternalPayloadEvaluationSet(ContractModel):
    factor_name: str = Field(min_length=1, max_length=128)
    primary_engine: EvaluationEngine = EvaluationEngine.ALPHALENS
    alphalens_payloads: list[AlphalensMetricPayload] = Field(default_factory=list)
    qlib_payloads: list[QlibMetricPayload] = Field(default_factory=list)
    vectorbt_payloads: list[VectorbtMetricPayload] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_payload_set(self) -> "ExternalPayloadEvaluationSet":
        if not self.alphalens_payloads and not self.qlib_payloads and not self.vectorbt_payloads:
            raise ValueError("at least one external payload is required")
        if self.primary_engine not in _SUPPORTED_EXTERNAL_ENGINES:
            raise ValueError("primary_engine must be alphalens, qlib, or vectorbt")
        self._validate_payload_factor_names()
        return self

    def _validate_payload_factor_names(self) -> None:
        normalized_factor_name = self.factor_name.strip().lower()
        payload_factor_names = [
            payload.factor_name
            for payload in [
                *self.alphalens_payloads,
                *self.qlib_payloads,
                *self.vectorbt_payloads,
            ]
        ]
        invalid_factor_names = [
            factor_name
            for factor_name in payload_factor_names
            if factor_name != normalized_factor_name
        ]
        if invalid_factor_names:
            raise ValueError("all external payload factor names must match factor_name")


def build_external_payload_evaluation_results(
    *,
    payload_set: ExternalPayloadEvaluationSet,
) -> list[FactorEvaluationResult]:
    return [
        *[
            run_alphalens_payload_evaluation(payload=payload)
            for payload in payload_set.alphalens_payloads
        ],
        *[
            run_qlib_payload_evaluation(payload=payload)
            for payload in payload_set.qlib_payloads
        ],
        *[
            run_vectorbt_payload_evaluation(payload=payload)
            for payload in payload_set.vectorbt_payloads
        ],
    ]


def build_external_payload_comparison_report(
    *,
    payload_set: ExternalPayloadEvaluationSet,
) -> FactorComparisonReport:
    evaluation_results = build_external_payload_evaluation_results(payload_set=payload_set)
    primary_result = _select_primary_result(
        evaluation_results=evaluation_results,
        primary_engine=payload_set.primary_engine,
    )
    additional_results = [
        result
        for result in evaluation_results
        if result is not primary_result
    ]

    return build_factor_comparison_report(
        primary_result=primary_result,
        additional_results=additional_results,
    )


def _select_primary_result(
    *,
    evaluation_results: list[FactorEvaluationResult],
    primary_engine: EvaluationEngine,
) -> FactorEvaluationResult:
    for result in evaluation_results:
        if result.evaluation_engine == primary_engine:
            return result
    raise ValueError("primary_engine must have at least one matching payload")


_SUPPORTED_EXTERNAL_ENGINES = {
    EvaluationEngine.ALPHALENS,
    EvaluationEngine.QLIB,
    EvaluationEngine.VECTORBT,
}
