import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchFactorValidationReview, fetchOverview } from "./api";
import type {
  FactorValidationArtifactSummary,
  FactorValidationReviewResponse,
  OpsOverviewResponse,
  ServiceHealth,
  ServiceStatus,
  ValidationDecision,
} from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";
type DashboardView = "overview" | "factor-validation";

interface NavItem {
  id: DashboardView | "data-hub" | "factor-lab" | "artifacts";
  label: string;
  is_enabled: boolean;
}

const SERVICE_LABELS: Record<string, string> = {
  quant_data_hub: "Data Hub",
  quant_factor_lab: "Factor Lab",
  quant_factor_validation: "Factor Validation",
};

const STATUS_LABELS: Record<ServiceStatus, string> = {
  ok: "正常",
  degraded: "需关注",
  down: "不可用",
};

const DECISION_LABELS: Record<ValidationDecision, string> = {
  insufficient_data: "样本不足",
  review_required: "需要审核",
  candidate_pass: "候选通过",
  candidate_reject: "候选拒绝",
};

const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: "Overview", is_enabled: true },
  { id: "data-hub", label: "Data Hub", is_enabled: false },
  { id: "factor-lab", label: "Factor Lab", is_enabled: false },
  { id: "factor-validation", label: "Validation", is_enabled: true },
  { id: "artifacts", label: "Artifacts", is_enabled: false },
];

export function App() {
  const [activeView, setActiveView] = useState<DashboardView>("overview");
  const [overview, setOverview] = useState<OpsOverviewResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null);
  const [validationReview, setValidationReview] = useState<FactorValidationReviewResponse | null>(null);
  const [validationLoadState, setValidationLoadState] = useState<LoadState>("idle");
  const [validationErrorMessage, setValidationErrorMessage] = useState<string | null>(null);

  const loadOverview = useCallback(async () => {
    setLoadState((currentState) => (currentState === "ready" ? "ready" : "loading"));
    setErrorMessage(null);

    try {
      const response = await fetchOverview();
      setOverview(response);
      setLastLoadedAt(new Date());
      setLoadState("ready");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "overview request failed");
      setLoadState("error");
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const loadFactorValidationReview = useCallback(async () => {
    setValidationLoadState((currentState) => (currentState === "ready" ? "ready" : "loading"));
    setValidationErrorMessage(null);

    try {
      const response = await fetchFactorValidationReview();
      setValidationReview(response);
      setValidationLoadState("ready");
    } catch (error) {
      setValidationErrorMessage(
        error instanceof Error ? error.message : "factor validation review request failed",
      );
      setValidationLoadState("error");
    }
  }, []);

  useEffect(() => {
    if (activeView !== "factor-validation") return;
    if (validationReview !== null) return;
    void loadFactorValidationReview();
  }, [activeView, loadFactorValidationReview, validationReview]);

  const primaryStatus = overview?.status ?? "down";
  const generatedAt = overview ? formatDateTime(overview.generated_at) : "等待数据";
  const updatedAt = lastLoadedAt ? formatTime(lastLoadedAt.toISOString()) : "未刷新";
  const refreshActiveView = activeView === "overview" ? loadOverview : loadFactorValidationReview;
  const pageTitle = activeView === "overview" ? "核心量化服务状态" : "因子验证审核视图";

  return (
    <main className="shell">
      <aside className="rail" aria-label="Dashboard navigation">
        <div className="brand-block">
          <span className="brand-mark">ZQ</span>
          <div>
            <p className="eyebrow">Zeta Quant</p>
            <h1>Ops Console</h1>
          </div>
        </div>
        <nav className="rail-nav" aria-label="Primary">
          {NAV_ITEMS.map((item) => (
            <button
              className={`rail-nav-item ${activeView === item.id ? "active" : ""}`}
              disabled={!item.is_enabled}
              key={item.id}
              type="button"
              onClick={() => {
                if (!item.is_enabled) return;
                setActiveView(item.id as DashboardView);
              }}
            >
              {item.label}
            </button>
          ))}
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">运行总览</p>
            <h2>{pageTitle}</h2>
          </div>
          <button className="refresh-button" type="button" onClick={refreshActiveView}>
            刷新状态
          </button>
        </header>

        {activeView === "overview" ? (
          <>
            <section className={`status-band status-${primaryStatus}`}>
              <StatusSpine services={overview?.services ?? []} fallbackStatus={primaryStatus} />
              <div className="status-copy">
                <span className="status-kicker">Pipeline status</span>
                <strong>{resolveOverviewLabel(primaryStatus)}</strong>
                <span>生成时间 {generatedAt}</span>
              </div>
              <MetricsStrip overview={overview} />
            </section>

            {loadState === "error" ? (
              <section className="notice error" role="alert">
                <strong>Overview API 暂时不可用</strong>
                <span>{errorMessage}</span>
              </section>
            ) : null}

            {loadState === "loading" && overview === null ? (
              <section className="notice">
                <strong>正在读取服务状态</strong>
                <span>连接 quant_ops_api</span>
              </section>
            ) : null}

            <section className="service-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">Service checks</p>
                  <h3>服务健康</h3>
                </div>
                <span className="muted">本地更新时间 {updatedAt}</span>
              </div>
              <ServiceTable services={overview?.services ?? []} />
            </section>
          </>
        ) : (
          <section className="validation-view">
            <FactorValidationReviewPanel
              errorMessage={validationErrorMessage}
              loadState={validationLoadState}
              review={validationReview}
            />
          </section>
        )}
      </section>
    </main>
  );
}

function MetricsStrip({ overview }: { overview: OpsOverviewResponse | null }) {
  const metrics = useMemo(
    () => [
      { label: "服务数", value: overview?.service_count ?? 0 },
      { label: "正常", value: overview?.healthy_count ?? 0 },
      { label: "需关注", value: overview?.degraded_count ?? 0 },
      { label: "不可用", value: overview?.down_count ?? 0 },
    ],
    [overview],
  );

  return (
    <div className="metrics-strip">
      {metrics.map((metric) => (
        <div className="metric" key={metric.label}>
          <span>{metric.label}</span>
          <strong>{metric.value}</strong>
        </div>
      ))}
    </div>
  );
}

function StatusSpine({
  services,
  fallbackStatus,
}: {
  services: ServiceHealth[];
  fallbackStatus: ServiceStatus;
}) {
  const spineServices = services.length > 0 ? services : [{ name: "pending", status: fallbackStatus }];

  return (
    <div className="status-spine" aria-label="Service status spine">
      {spineServices.map((service) => (
        <span className={`spine-segment segment-${service.status}`} key={service.name} />
      ))}
    </div>
  );
}

function ServiceTable({ services }: { services: ServiceHealth[] }) {
  if (services.length === 0) {
    return (
      <div className="empty-state">
        <strong>暂无服务状态</strong>
        <span>等待 quant_ops_api 返回 overview 数据。</span>
      </div>
    );
  }

  return (
    <div className="service-table">
      <div className="service-row header">
        <span>服务</span>
        <span>状态</span>
        <span>延迟</span>
        <span>检查时间</span>
      </div>
      {services.map((service) => (
        <div className="service-row" key={service.name}>
          <div className="service-name">
            <span className={`status-dot dot-${service.status}`} />
            <div>
              <strong>{SERVICE_LABELS[service.name] ?? service.name}</strong>
              <span>{service.base_url}</span>
            </div>
          </div>
          <span className={`status-pill pill-${service.status}`}>{STATUS_LABELS[service.status]}</span>
          <span>{formatLatency(service.latency_ms)}</span>
          <span>{formatTime(service.checked_at)}</span>
        </div>
      ))}
    </div>
  );
}

function FactorValidationReviewPanel({
  review,
  loadState,
  errorMessage,
}: {
  review: FactorValidationReviewResponse | null;
  loadState: LoadState;
  errorMessage: string | null;
}) {
  if (loadState === "error") {
    return (
      <section className="notice error" role="alert">
        <strong>因子验证审核摘要暂时不可用</strong>
        <span>{errorMessage}</span>
      </section>
    );
  }

  if (review === null) {
    return (
      <section className="notice">
        <strong>正在读取因子验证审核摘要</strong>
        <span>连接 quant_ops_api</span>
      </section>
    );
  }

  const metric = review.latest_metric;

  return (
    <>
      <section className={`validation-hero decision-${metric.decision}`}>
        <div>
          <p className="eyebrow">Factor validation</p>
          <h3>{metric.factor_name}</h3>
          <span className="muted">{metric.run_id}</span>
        </div>
        <div className="decision-block">
          <span>审核状态</span>
          <strong>{DECISION_LABELS[metric.decision]}</strong>
        </div>
        <div className="metric-grid compact">
          <MetricTile label="样本" value={`${metric.effective_sample_count}/${metric.sample_count}`} />
          <MetricTile label="覆盖率" value={formatRatio(metric.coverage_ratio)} />
          <MetricTile label="IC" value={formatNumber(metric.ic_mean)} />
          <MetricTile label="Rank IC" value={formatNumber(metric.rank_ic_mean)} />
        </div>
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Review findings</p>
            <h3>审核发现</h3>
          </div>
          <span className="status-pill pill-degraded">{review.persistence_status}</span>
        </div>
        <div className="finding-list">
          {review.findings.map((finding) => (
            <div className={`finding-item severity-${finding.severity}`} key={finding.code}>
              <strong>{finding.code}</strong>
              <span>{finding.message}</span>
            </div>
          ))}
        </div>
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Manifest preview</p>
            <h3>{review.manifest.manifest_id}</h3>
          </div>
          <span className="muted">{formatDateTime(review.generated_at)}</span>
        </div>
        <ArtifactTable artifacts={review.manifest.artifacts} />
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Next review actions</p>
            <h3>后续动作</h3>
          </div>
        </div>
        <div className="action-list">
          {[...review.recommended_actions, ...review.limitations].map((action) => (
            <span key={action}>{action}</span>
          ))}
        </div>
      </section>
    </>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ArtifactTable({ artifacts }: { artifacts: FactorValidationArtifactSummary[] }) {
  if (artifacts.length === 0) {
    return (
      <div className="empty-state">
        <strong>暂无产物</strong>
        <span>等待 manifest 返回 artifact 列表。</span>
      </div>
    );
  }

  return (
    <div className="artifact-table">
      <div className="artifact-row header">
        <span>类型</span>
        <span>Schema</span>
        <span>Object key</span>
      </div>
      {artifacts.map((artifact) => (
        <div className="artifact-row" key={artifact.artifact_id}>
          <strong>{artifact.artifact_type}</strong>
          <span>{artifact.schema_version}</span>
          <span>{artifact.object_key ?? "--"}</span>
        </div>
      ))}
    </div>
  );
}

function resolveOverviewLabel(status: ServiceStatus): string {
  if (status === "ok") return "主链路健康";
  if (status === "degraded") return "部分服务需关注";
  return "主链路不可用";
}

function formatLatency(latencyMs: number | null): string {
  if (latencyMs === null) return "--";
  return `${latencyMs.toFixed(1)} ms`;
}

function formatDateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function formatRatio(value: number | null): string {
  if (value === null) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value: number | null): string {
  if (value === null) return "--";
  return value.toFixed(3);
}
