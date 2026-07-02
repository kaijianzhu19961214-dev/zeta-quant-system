export type ServiceStatus = "ok" | "degraded" | "down";
export type OverviewStatus = "ok" | "degraded" | "down";

export interface ServiceHealth {
  name: string;
  base_url: string;
  status: ServiceStatus;
  checked_at: string;
  latency_ms: number | null;
  http_status_code: number | null;
  error_message: string | null;
}

export interface OpsOverviewResponse {
  status: OverviewStatus;
  generated_at: string;
  services: ServiceHealth[];
  service_count: number;
  healthy_count: number;
  degraded_count: number;
  down_count: number;
}

export type MarketDataServiceStatus = "ok" | "degraded";
export type PriceModeName = "raw" | "qfq" | "hfq";
export type TimeframeName = "1m" | "5m" | "1d";
export type MarketDecimal = string | number | null;

export interface QfqBatchSummary {
  batch_id: string;
  qfq_base_date: string;
  status: string;
  description: string | null;
  created_at: string | null;
  finished_at: string | null;
}

export interface MarketPriceModeStatus {
  price_mode: PriceModeName;
  display_name: string;
  storage_object: string;
  source_relation: string;
  requires_batch_id: boolean;
  available: boolean;
  latest_batch_id: string | null;
  latest_qfq_base_date: string | null;
}

export interface MarketDataPriceModeOverview {
  status: MarketDataServiceStatus;
  generated_at: string;
  qfq_batch_count: number;
  latest_qfq_batch: QfqBatchSummary | null;
  price_modes: MarketPriceModeStatus[];
  limitations: string[];
}

export type StorageRoleName = "postgresql" | "clickhouse" | "minio" | "redis";

export interface MarketDataSourceCoverageItem {
  timeframe: TimeframeName;
  storage_object: string;
  dataset_code: string;
  source_name: string;
  row_count: number;
  symbol_count: number;
  trading_day_count: number;
  min_date: string | null;
  max_date: string | null;
  duplicate_key_rows: number;
}

export interface MarketDataStorageRole {
  storage_name: StorageRoleName;
  display_name: string;
  responsibility: string;
  current_usage: string;
  stores_market_bars: boolean;
}

export interface MarketDataSourceCoverageResponse {
  status: MarketDataServiceStatus;
  generated_at: string;
  row_count: number;
  coverage: MarketDataSourceCoverageItem[];
  storage_roles: MarketDataStorageRole[];
  limitations: string[];
}

export interface MarketDataBarsSampleRequest {
  symbol: string;
  timeframe: TimeframeName;
  start: string;
  end: string;
  price_mode: PriceModeName;
  batch_id?: string | null;
  fields?: string[] | null;
  limit: number;
}

export interface MarketBarsMeta {
  timeframe: TimeframeName;
  price_mode: PriceModeName;
  row_count: number;
  dataset_code: string | null;
  batch_id: string | null;
  qfq_base_date: string | null;
}

export interface MarketBar {
  symbol: string;
  trade_date: string | null;
  trade_time: string | null;
  open_price: MarketDecimal;
  high_price: MarketDecimal;
  low_price: MarketDecimal;
  close_price: MarketDecimal;
  volume: MarketDecimal;
  turnover: MarketDecimal;
  vwap: MarketDecimal;
  adjustment_factor: MarketDecimal;
}

export interface MarketDataBarsSampleResponse {
  generated_at: string;
  request: MarketDataBarsSampleRequest;
  meta: MarketBarsMeta;
  rows: MarketBar[];
  limitations: string[];
}

export interface FactorCalculationMeta {
  factor_name: string;
  algorithm_id: string | null;
  algorithm_version: string | null;
  algorithm_source_library: string | null;
  asset_class: string;
  factor_mode: string;
  factor_family: string;
  timeframe: TimeframeName;
  price_mode: PriceModeName;
  row_count: number;
  lookback_window: number;
  universe_name: string;
  data_source: string;
  data_version: string | null;
  factor_version: string;
  run_id: string | null;
  dataset_code: string | null;
  batch_id: string | null;
}

export interface FactorDailyValue {
  symbol: string;
  trade_date: string;
  factor_name: string;
  factor_value: MarketDecimal;
  asset_class: string;
  factor_mode: string;
  factor_family: string;
  universe_name: string;
  data_source: string;
  data_version: string | null;
  factor_version: string;
  run_id: string | null;
  created_at: string | null;
}

export interface FactorCalculationResponse {
  meta: FactorCalculationMeta;
  rows: FactorDailyValue[];
}

export type ValidationDecision =
  | "insufficient_data"
  | "review_required"
  | "candidate_pass"
  | "candidate_reject";

export type PersistenceStatus = "not_persisted" | "persisted";
export type FindingSeverity = "info" | "warning" | "error";
export type ExternalEvaluationEngine = "alphalens" | "qlib" | "vectorbt";
export type ExternalMetricValue = string | number;
export type ArtifactReadStatus = "artifact_loaded" | "preview_fallback";
export type AlgorithmRole = "factor_generator" | "model" | "validation_engine" | "comparison_engine";
export type AlgorithmStatus = "available" | "planned" | "disabled" | "deprecated";
export type AlgorithmOutputKind = "factor_values" | "forecast" | "volatility" | "signal" | "diagnostics";
export type AlgorithmReviewGateCategory =
  | "hypothesis"
  | "data"
  | "construction"
  | "leakage"
  | "validation"
  | "operations";
export type AlgorithmReviewGateStatus = "satisfied" | "missing" | "not_applicable";
export type AlgorithmReviewEvidenceStatus = "submitted" | "accepted" | "rejected";
export type AlgorithmGatePromotionDecision =
  | "met_by_registry"
  | "met_by_accepted_evidence"
  | "blocked_missing_evidence"
  | "blocked_rejected_evidence"
  | "not_applicable";
export type AlgorithmPromotionDecision = "promotable" | "blocked";
export type AlgorithmReviewEvidenceType =
  | "research_note"
  | "notebook"
  | "artifact"
  | "validation_report"
  | "external_link"
  | "manual_note";

export interface AlgorithmParameterSpec {
  name: string;
  value_type: "integer" | "number" | "string" | "boolean";
  description: string;
  default_value: number | string | boolean | null;
  minimum: number | null;
  maximum: number | null;
}

export interface AlgorithmCapability {
  asset_classes: string[];
  factor_modes: string[];
  factor_families: string[];
  timeframes: string[];
  output_kinds: AlgorithmOutputKind[];
}

export interface AlgorithmReviewGate {
  gate_id: string;
  category: AlgorithmReviewGateCategory;
  title: string;
  description: string;
  status: AlgorithmReviewGateStatus;
  evidence: string | null;
  is_required: boolean;
}

export interface AlgorithmReviewGateEvidenceRecord {
  evidence_id: string;
  algorithm_id: string;
  gate_id: string;
  submitted_by: string;
  evidence_type: AlgorithmReviewEvidenceType;
  evidence_source: string;
  summary: string;
  artifact_id: string | null;
  artifact_uri: string | null;
  source_url: string | null;
  notes: string[];
  gate_category: AlgorithmReviewGateCategory;
  gate_title: string;
  previous_gate_status: AlgorithmReviewGateStatus;
  evidence_status: AlgorithmReviewEvidenceStatus;
  submitted_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  review_comment: string | null;
  is_required: boolean;
}

export interface AlgorithmReviewGateEvidenceListResponse {
  algorithm_id: string;
  gate_id: string | null;
  records: AlgorithmReviewGateEvidenceRecord[];
  total_count: number;
  persistence_status: PersistenceStatus;
  limitations: string[];
}

export interface AlgorithmGatePromotionFinding {
  gate_id: string;
  gate_title: string;
  gate_status: AlgorithmReviewGateStatus;
  decision: AlgorithmGatePromotionDecision;
  is_required: boolean;
  is_met: boolean;
  accepted_evidence_count: number;
  latest_evidence_status: AlgorithmReviewEvidenceStatus | null;
  message: string;
}

export interface AlgorithmPromotionReadinessResponse {
  algorithm_id: string;
  current_status: AlgorithmStatus;
  decision: AlgorithmPromotionDecision;
  can_promote: boolean;
  required_gate_count: number;
  met_required_gate_count: number;
  missing_required_gate_ids: string[];
  rejected_required_gate_ids: string[];
  findings: AlgorithmGatePromotionFinding[];
  generated_at: string;
  limitations: string[];
}

export interface AlgorithmSpec {
  algorithm_id: string;
  display_name: string;
  role: AlgorithmRole;
  status: AlgorithmStatus;
  version: string;
  description: string;
  source_library: string | null;
  source_url: string | null;
  adapter_module: string | null;
  capability: AlgorithmCapability;
  parameters: AlgorithmParameterSpec[];
  tags: string[];
  research_notes: string[];
  limitations: string[];
  review_gates: AlgorithmReviewGate[];
}

export interface ExternalMetricPayload {
  factor_name: string;
  start_date: string;
  end_date: string;
  forward_days: number;
  sample_count: number;
  effective_sample_count: number;
  metric_values?: Record<string, ExternalMetricValue>;
  source_version?: string | null;
  source_run_id?: string | null;
  recorder_id?: string | null;
  experiment_name?: string | null;
  portfolio_name?: string | null;
  parameter_set_id?: string | null;
  warnings?: string[];
  notes?: string[];
}

export interface ExternalPayloadComparisonRequest {
  factor_name: string;
  primary_engine: ExternalEvaluationEngine;
  alphalens_payloads: ExternalMetricPayload[];
  qlib_payloads: ExternalMetricPayload[];
  vectorbt_payloads: ExternalMetricPayload[];
}

export interface FactorValidationMetricSummary {
  factor_name: string;
  validation_version: string;
  run_id: string;
  forward_days: number;
  sample_count: number;
  effective_sample_count: number;
  coverage_ratio: number | null;
  missing_ratio: number | null;
  ic_mean: number | null;
  rank_ic_mean: number | null;
  ic_ir: number | null;
  group_count: number;
  group_return_spread_mean: number | null;
  decision: ValidationDecision;
}

export interface FactorValidationFindingSummary {
  severity: FindingSeverity;
  code: string;
  message: string;
}

export interface FactorValidationArtifactSummary {
  artifact_id: string;
  artifact_type: string;
  object_key: string | null;
  schema_version: string;
  persistence_status: PersistenceStatus;
}

export interface FactorScoreComponentSummary {
  name: string;
  raw_value: number | null;
  score: number;
  max_score: number;
  reason: string;
}

export interface FactorScoreCardSummary {
  factor_name: string;
  evaluation_engine: string;
  final_score: number;
  max_score: number;
  review_decision: ValidationDecision;
  score_components: FactorScoreComponentSummary[];
  warnings: string[];
}

export interface FactorComparisonSummary {
  primary_engine: string;
  engine_count: number;
  has_engine_disagreement: boolean;
  comparison_summary: string;
}

export interface FactorValidationMetric {
  factor_name: string;
  evaluation_engine: string;
  start_date: string;
  end_date: string;
  forward_days: number;
  sample_count: number;
  effective_sample_count: number;
  coverage_ratio: number | null;
  missing_ratio: number | null;
  ic_mean: number | null;
  rank_ic_mean: number | null;
  ic_ir: number | null;
  group_count: number;
  group_return_spread_mean: number | null;
}

export interface FactorValidationReport {
  decision: ValidationDecision;
  summary: string;
  findings: FactorValidationFindingSummary[];
  recommended_actions: string[];
}

export interface FactorScoreCard {
  factor_name: string;
  evaluation_engine: string;
  final_score: number;
  max_score: number;
  review_decision: ValidationDecision;
  score_components: FactorScoreComponentSummary[];
  warnings: string[];
}

export interface FactorEvaluationResult {
  factor_name: string;
  evaluation_engine: string;
  metrics: FactorValidationMetric;
  report: FactorValidationReport | null;
  score_card: FactorScoreCard | null;
}

export interface FactorComparisonReport {
  factor_name: string;
  primary_engine: string;
  engine_results: FactorEvaluationResult[];
  engine_count: number;
  has_engine_disagreement: boolean;
  comparison_summary: string;
}

export interface FactorComparisonArtifactReference {
  artifact_id: string;
  task_id: string;
  storage_type: string;
  bucket_name: string | null;
  object_key: string | null;
  uri: string | null;
  file_size_bytes: number | null;
  schema_version: string | null;
  created_at: string | null;
}

export interface ExternalPayloadComparisonPreviewResponse {
  generated_at: string;
  source: string;
  comparison_report: FactorComparisonReport;
  artifact_reference: FactorComparisonArtifactReference | null;
  artifact_read_status: ArtifactReadStatus;
  artifact_read_reason: string | null;
  artifact_read_message: string | null;
  limitations: string[];
}

export interface FactorValidationManifestSummary {
  manifest_id: string;
  task_id: string;
  task_name: string;
  task_type: string;
  persistence_status: PersistenceStatus;
  artifact_count: number;
  artifacts: FactorValidationArtifactSummary[];
}

export interface FactorValidationReviewResponse {
  generated_at: string;
  source: string;
  persistence_status: PersistenceStatus;
  latest_metric: FactorValidationMetricSummary;
  findings: FactorValidationFindingSummary[];
  recommended_actions: string[];
  score_card: FactorScoreCardSummary | null;
  comparison: FactorComparisonSummary | null;
  manifest: FactorValidationManifestSummary;
  limitations: string[];
}

export type TaskLedgerStatus =
  | "created"
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled"
  | "canceled";

export interface TaskLedgerItem {
  task_id: string;
  task_type: string;
  task_name: string;
  owner: string | null;
  status: TaskLedgerStatus;
  input_params: Record<string, unknown>;
  output_summary: Record<string, unknown>;
  error_message: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  artifact_count: number;
}

export interface ArtifactLedgerItem {
  artifact_id: string;
  task_id: string;
  artifact_type: string;
  storage_type: string;
  bucket_name: string | null;
  object_key: string | null;
  uri: string | null;
  file_size_bytes: number | null;
  schema_version: string | null;
  metadata: Record<string, unknown>;
  created_at: string | null;
}

export interface ArtifactLedgerResponse {
  generated_at: string;
  source: string;
  persistence_status: PersistenceStatus;
  task_count: number;
  artifact_count: number;
  tasks: TaskLedgerItem[];
  artifacts: ArtifactLedgerItem[];
  limitations: string[];
}
