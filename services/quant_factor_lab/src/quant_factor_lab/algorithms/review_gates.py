from quant_contracts import AlgorithmReviewGate


def build_momentum_review_gates() -> list[AlgorithmReviewGate]:
    return [
        AlgorithmReviewGate(
            gate_id="hypothesis_documented",
            category="hypothesis",
            title="Hypothesis documented",
            description="Economic intuition, target horizon, and supported factor modes are documented.",
            status="satisfied",
            evidence="Momentum captures prior close-to-close return over the requested lookback window.",
        ),
        AlgorithmReviewGate(
            gate_id="data_policy_fixed",
            category="data",
            title="Data policy fixed",
            description="Required market fields and daily timeframe are explicit.",
            status="satisfied",
            evidence="Adapter requires symbol, trade_date, close_price, volume, and turnover.",
        ),
        AlgorithmReviewGate(
            gate_id="construction_policy_fixed",
            category="construction",
            title="Construction policy fixed",
            description="Factor construction and lookback window validation are deterministic.",
            status="satisfied",
            evidence="factor_name momentum_*d must match lookback_window before calculation.",
        ),
        AlgorithmReviewGate(
            gate_id="leakage_audit",
            category="leakage",
            title="Leakage audit",
            description="Future-function and same-day tradability risks are documented.",
            status="satisfied",
            evidence="Each factor value only references earlier close prices inside the lookback window.",
        ),
        AlgorithmReviewGate(
            gate_id="validation_evidence",
            category="validation",
            title="Validation evidence",
            description="IC, Rank IC, grouping behavior, and artifact manifest evidence are available.",
            status="satisfied",
            evidence="Baseline momentum can be verified through quant_factor_validation smoke and manifest artifacts.",
        ),
        AlgorithmReviewGate(
            gate_id="adapter_tests",
            category="operations",
            title="Adapter tests",
            description="Registry and calculation service tests cover adapter resolution and output metadata.",
            status="satisfied",
            evidence="quant_factor_lab unittest suite covers registry resolution and momentum calculation routes.",
        ),
    ]


def build_planned_volatility_review_gates() -> list[AlgorithmReviewGate]:
    return [
        AlgorithmReviewGate(
            gate_id="hypothesis_documented",
            category="hypothesis",
            title="Hypothesis documented",
            description="Volatility and leverage-effect hypothesis is documented before implementation.",
            status="satisfied",
            evidence="GARCH-family candidate models target conditional volatility and asymmetric shock response.",
        ),
        AlgorithmReviewGate(
            gate_id="data_policy_fixed",
            category="data",
            title="Data policy fixed",
            description="Return input, adjustment mode, minimum history, and missing data handling must be fixed.",
            status="missing",
        ),
        AlgorithmReviewGate(
            gate_id="construction_policy_fixed",
            category="construction",
            title="Construction policy fixed",
            description="Window length, refit cadence, output field, and factor_value mapping must be fixed.",
            status="missing",
        ),
        AlgorithmReviewGate(
            gate_id="leakage_audit",
            category="leakage",
            title="Leakage audit",
            description="Same-day tradability, fit window alignment, and contract roll leakage must be reviewed.",
            status="missing",
        ),
        AlgorithmReviewGate(
            gate_id="validation_evidence",
            category="validation",
            title="Validation evidence",
            description="IC, Rank IC, decay, quantile behavior, turnover, and cost sensitivity must be recorded.",
            status="missing",
        ),
        AlgorithmReviewGate(
            gate_id="adapter_tests",
            category="operations",
            title="Adapter tests",
            description="Unit tests, sample data tests, and artifact output checks must pass before promotion.",
            status="missing",
        ),
    ]
