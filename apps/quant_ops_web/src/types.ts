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
  manifest: FactorValidationManifestSummary;
  limitations: string[];
}
