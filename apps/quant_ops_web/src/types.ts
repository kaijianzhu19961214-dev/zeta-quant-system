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
