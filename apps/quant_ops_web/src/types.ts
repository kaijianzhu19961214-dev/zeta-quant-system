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
