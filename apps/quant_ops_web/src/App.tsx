import { useCallback, useEffect, useMemo, useState } from "react";

import { fetchOverview } from "./api";
import type { OpsOverviewResponse, ServiceHealth, ServiceStatus } from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";

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

export function App() {
  const [overview, setOverview] = useState<OpsOverviewResponse | null>(null);
  const [loadState, setLoadState] = useState<LoadState>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [lastLoadedAt, setLastLoadedAt] = useState<Date | null>(null);

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

  const primaryStatus = overview?.status ?? "down";
  const generatedAt = overview ? formatDateTime(overview.generated_at) : "等待数据";
  const updatedAt = lastLoadedAt ? formatTime(lastLoadedAt.toISOString()) : "未刷新";

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
          <span className="rail-nav-item active">Overview</span>
          <span className="rail-nav-item">Data Hub</span>
          <span className="rail-nav-item">Factor Lab</span>
          <span className="rail-nav-item">Validation</span>
          <span className="rail-nav-item">Artifacts</span>
        </nav>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">运行总览</p>
            <h2>核心量化服务状态</h2>
          </div>
          <button className="refresh-button" type="button" onClick={loadOverview}>
            刷新状态
          </button>
        </header>

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
