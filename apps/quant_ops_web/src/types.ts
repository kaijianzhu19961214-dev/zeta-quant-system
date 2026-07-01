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
