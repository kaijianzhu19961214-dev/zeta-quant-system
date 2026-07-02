import { useCallback, useEffect, useMemo, useState } from "react";

import {
  fetchArtifactLedger,
  fetchExternalPayloadComparisonPreview,
  fetchFactorLabAlgorithms,
  fetchFactorValidationReview,
  fetchOverview,
} from "./api";
import type {
  AlgorithmReviewGate,
  AlgorithmSpec,
  ArtifactLedgerItem,
  ArtifactLedgerResponse,
  ExternalPayloadComparisonPreviewResponse,
  FactorEvaluationResult,
  FactorValidationArtifactSummary,
  FactorValidationReviewResponse,
  OpsOverviewResponse,
  ServiceHealth,
  ServiceStatus,
  ValidationDecision,
} from "./types";

type LoadState = "idle" | "loading" | "ready" | "error";
type DashboardView = "overview" | "factor-lab" | "factor-validation" | "artifacts";

interface NavItem {
  id: DashboardView | "data-hub" | "factor-lab";
  label: string;
  is_enabled: boolean;
}

const SERVICE_LABELS: Record<string, string> = {
  quant_data_hub: bilingualLabel("数据中心", "Data Hub"),
  quant_factor_lab: bilingualLabel("因子实验室", "Factor Lab"),
  quant_factor_validation: bilingualLabel("因子验证", "Factor Validation"),
};

const STATUS_LABELS: Record<ServiceStatus, string> = {
  ok: bilingualLabel("正常", "OK"),
  degraded: bilingualLabel("需关注", "Degraded"),
  down: bilingualLabel("不可用", "Down"),
};

const DECISION_LABELS: Record<ValidationDecision, string> = {
  insufficient_data: bilingualLabel("样本不足", "Insufficient Data"),
  review_required: bilingualLabel("需要审核", "Review Required"),
  candidate_pass: bilingualLabel("候选通过", "Candidate Pass"),
  candidate_reject: bilingualLabel("候选拒绝", "Candidate Reject"),
};

const ALGORITHM_STATUS_LABELS: Record<string, string> = {
  available: bilingualLabel("可运行", "Available"),
  planned: bilingualLabel("候选", "Planned"),
  disabled: bilingualLabel("停用", "Disabled"),
  deprecated: bilingualLabel("废弃", "Deprecated"),
};

const ALGORITHM_REVIEW_GATE_STATUS_LABELS: Record<string, string> = {
  satisfied: bilingualLabel("已满足", "Satisfied"),
  missing: bilingualLabel("缺证据", "Missing"),
  not_applicable: bilingualLabel("不适用", "N/A"),
};

const ALGORITHM_REVIEW_GATE_TITLE_LABELS: Record<string, string> = {
  hypothesis_documented: bilingualLabel("假设已记录", "Hypothesis Documented"),
  data_policy_fixed: bilingualLabel("数据口径已固定", "Data Policy Fixed"),
  construction_policy_fixed: bilingualLabel("构造规则已固定", "Construction Policy Fixed"),
  leakage_audit: bilingualLabel("未来函数审计", "Leakage Audit"),
  validation_evidence: bilingualLabel("验证证据", "Validation Evidence"),
  adapter_tests: bilingualLabel("适配器测试", "Adapter Tests"),
};

const ALGORITHM_REVIEW_GATE_CATEGORY_LABELS: Record<string, string> = {
  hypothesis: bilingualLabel("假设", "Hypothesis"),
  data: bilingualLabel("数据", "Data"),
  construction: bilingualLabel("构造", "Construction"),
  leakage: bilingualLabel("未来函数", "Leakage"),
  validation: bilingualLabel("验证", "Validation"),
  operations: bilingualLabel("运维", "Operations"),
};

const ALGORITHM_REVIEW_GATE_BODY_LABELS: Record<string, string> = {
  hypothesis_documented: bilingualLabel(
    "需要明确经济含义、目标周期、适用资产与因子模式。",
    "Economic intuition, target horizon, asset class, and factor mode must be documented.",
  ),
  data_policy_fixed: bilingualLabel(
    "需要固定输入字段、复权口径、最小历史窗口和缺失值处理规则。",
    "Input fields, adjustment mode, minimum history, and missing-data policy must be fixed.",
  ),
  construction_policy_fixed: bilingualLabel(
    "需要固定窗口长度、重算节奏、输出字段和 factor_value 映射规则。",
    "Window length, refit cadence, output fields, and factor_value mapping must be fixed.",
  ),
  leakage_audit: bilingualLabel(
    "需要审查同日可交易性、拟合窗口对齐和合约展期等未来函数风险。",
    "Same-day tradability, fit-window alignment, and roll leakage must be reviewed.",
  ),
  validation_evidence: bilingualLabel(
    "需要记录 IC、Rank IC、衰减、分组表现、换手和成本敏感性证据。",
    "IC, Rank IC, decay, grouping behavior, turnover, and cost sensitivity must be recorded.",
  ),
  adapter_tests: bilingualLabel(
    "需要通过单元测试、样本数据测试和产物输出检查后才能升级。",
    "Unit tests, sample-data tests, and artifact output checks must pass before promotion.",
  ),
};

const NAV_ITEMS: NavItem[] = [
  { id: "overview", label: bilingualLabel("总览", "Overview"), is_enabled: true },
  { id: "data-hub", label: bilingualLabel("数据中心", "Data Hub"), is_enabled: false },
  { id: "factor-lab", label: bilingualLabel("因子实验室", "Factor Lab"), is_enabled: true },
  { id: "factor-validation", label: bilingualLabel("因子验证", "Validation"), is_enabled: true },
  { id: "artifacts", label: bilingualLabel("产物账本", "Artifacts"), is_enabled: true },
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
  const [externalComparisonPreview, setExternalComparisonPreview] =
    useState<ExternalPayloadComparisonPreviewResponse | null>(null);
  const [externalComparisonLoadState, setExternalComparisonLoadState] = useState<LoadState>("idle");
  const [externalComparisonErrorMessage, setExternalComparisonErrorMessage] = useState<string | null>(null);
  const [factorAlgorithms, setFactorAlgorithms] = useState<AlgorithmSpec[] | null>(null);
  const [factorAlgorithmLoadState, setFactorAlgorithmLoadState] = useState<LoadState>("idle");
  const [factorAlgorithmErrorMessage, setFactorAlgorithmErrorMessage] = useState<string | null>(null);
  const [artifactLedger, setArtifactLedger] = useState<ArtifactLedgerResponse | null>(null);
  const [artifactLoadState, setArtifactLoadState] = useState<LoadState>("idle");
  const [artifactErrorMessage, setArtifactErrorMessage] = useState<string | null>(null);

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

  const loadExternalPayloadComparison = useCallback(async () => {
    setExternalComparisonLoadState((currentState) => (currentState === "ready" ? "ready" : "loading"));
    setExternalComparisonErrorMessage(null);

    try {
      const response = await fetchExternalPayloadComparisonPreview();
      setExternalComparisonPreview(response);
      setExternalComparisonLoadState("ready");
    } catch (error) {
      setExternalComparisonErrorMessage(
        error instanceof Error ? error.message : "external payload comparison request failed",
      );
      setExternalComparisonLoadState("error");
    }
  }, []);

  useEffect(() => {
    if (activeView !== "factor-validation") return;
    if (externalComparisonPreview !== null) return;
    if (externalComparisonLoadState !== "idle") return;
    void loadExternalPayloadComparison();
  }, [activeView, externalComparisonPreview, externalComparisonLoadState, loadExternalPayloadComparison]);

  const loadFactorAlgorithms = useCallback(async () => {
    setFactorAlgorithmLoadState((currentState) => (currentState === "ready" ? "ready" : "loading"));
    setFactorAlgorithmErrorMessage(null);

    try {
      const response = await fetchFactorLabAlgorithms();
      setFactorAlgorithms(response);
      setFactorAlgorithmLoadState("ready");
    } catch (error) {
      setFactorAlgorithmErrorMessage(
        error instanceof Error ? error.message : "factor lab algorithms request failed",
      );
      setFactorAlgorithmLoadState("error");
    }
  }, []);

  useEffect(() => {
    if (activeView !== "factor-lab") return;
    if (factorAlgorithms !== null) return;
    void loadFactorAlgorithms();
  }, [activeView, factorAlgorithms, loadFactorAlgorithms]);

  const loadArtifactLedger = useCallback(async () => {
    setArtifactLoadState((currentState) => (currentState === "ready" ? "ready" : "loading"));
    setArtifactErrorMessage(null);

    try {
      const response = await fetchArtifactLedger();
      setArtifactLedger(response);
      setArtifactLoadState("ready");
    } catch (error) {
      setArtifactErrorMessage(error instanceof Error ? error.message : "artifact ledger request failed");
      setArtifactLoadState("error");
    }
  }, []);

  useEffect(() => {
    if (activeView !== "artifacts") return;
    if (artifactLedger !== null) return;
    void loadArtifactLedger();
  }, [activeView, artifactLedger, loadArtifactLedger]);

  const primaryStatus = overview?.status ?? "down";
  const generatedAt = overview ? formatDateTime(overview.generated_at) : bilingualLabel("等待数据", "Waiting");
  const updatedAt = lastLoadedAt ? formatTime(lastLoadedAt.toISOString()) : bilingualLabel("未刷新", "Not refreshed");
  const refreshActiveView = resolveRefreshHandler({
    activeView,
    loadArtifactLedger,
    loadFactorAlgorithms,
    loadExternalPayloadComparison,
    loadFactorValidationReview,
    loadOverview,
  });
  const pageTitle = resolvePageTitle(activeView);

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
            <p className="eyebrow">{bilingualLabel("运行总览", "Operations Overview")}</p>
            <h2>{pageTitle}</h2>
          </div>
          <button className="refresh-button" type="button" onClick={refreshActiveView}>
            {bilingualLabel("刷新状态", "Refresh")}
          </button>
        </header>

        {activeView === "overview" ? (
          <>
            <section className={`status-band status-${primaryStatus}`}>
              <StatusSpine services={overview?.services ?? []} fallbackStatus={primaryStatus} />
              <div className="status-copy">
                <span className="status-kicker">{bilingualLabel("链路状态", "Pipeline Status")}</span>
                <strong>{resolveOverviewLabel(primaryStatus)}</strong>
                <span>{bilingualLabel("生成时间", "Generated at")} {generatedAt}</span>
              </div>
              <MetricsStrip overview={overview} />
            </section>

            {loadState === "error" ? (
              <section className="notice error" role="alert">
                <strong>{bilingualLabel("Overview API 暂时不可用", "Overview API unavailable")}</strong>
                <span>{errorMessage}</span>
              </section>
            ) : null}

            {loadState === "loading" && overview === null ? (
              <section className="notice">
                <strong>{bilingualLabel("正在读取服务状态", "Loading service status")}</strong>
                <span>{bilingualLabel("连接 quant_ops_api", "Connecting to quant_ops_api")}</span>
              </section>
            ) : null}

            <section className="service-panel">
              <div className="section-heading">
                <div>
                  <p className="eyebrow">{bilingualLabel("服务检查", "Service Checks")}</p>
                  <h3>{bilingualLabel("服务健康", "Service Health")}</h3>
                </div>
                <span className="muted">{bilingualLabel("本地更新时间", "Local updated at")} {updatedAt}</span>
              </div>
              <ServiceTable services={overview?.services ?? []} />
            </section>
          </>
        ) : activeView === "factor-validation" ? (
          <section className="validation-view">
            <FactorValidationReviewPanel
              comparisonErrorMessage={externalComparisonErrorMessage}
              comparisonLoadState={externalComparisonLoadState}
              comparisonPreview={externalComparisonPreview}
              errorMessage={validationErrorMessage}
              loadState={validationLoadState}
              onRunComparison={loadExternalPayloadComparison}
              review={validationReview}
            />
          </section>
        ) : activeView === "factor-lab" ? (
          <section className="validation-view">
            <FactorLabAlgorithmsPanel
              algorithms={factorAlgorithms}
              errorMessage={factorAlgorithmErrorMessage}
              loadState={factorAlgorithmLoadState}
            />
          </section>
        ) : (
          <section className="validation-view">
            <ArtifactLedgerPanel
              errorMessage={artifactErrorMessage}
              ledger={artifactLedger}
              loadState={artifactLoadState}
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
      { label: bilingualLabel("服务数", "Services"), value: overview?.service_count ?? 0 },
      { label: bilingualLabel("正常", "OK"), value: overview?.healthy_count ?? 0 },
      { label: bilingualLabel("需关注", "Degraded"), value: overview?.degraded_count ?? 0 },
      { label: bilingualLabel("不可用", "Down"), value: overview?.down_count ?? 0 },
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
        <strong>{bilingualLabel("暂无服务状态", "No Service Status")}</strong>
        <span>{bilingualLabel("等待 quant_ops_api 返回 overview 数据。", "Waiting for quant_ops_api overview data.")}</span>
      </div>
    );
  }

  return (
    <div className="service-table">
      <div className="service-row header">
        <span>{bilingualLabel("服务", "Service")}</span>
        <span>{bilingualLabel("状态", "Status")}</span>
        <span>{bilingualLabel("延迟", "Latency")}</span>
        <span>{bilingualLabel("检查时间", "Checked At")}</span>
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

function FactorLabAlgorithmsPanel({
  algorithms,
  loadState,
  errorMessage,
}: {
  algorithms: AlgorithmSpec[] | null;
  loadState: LoadState;
  errorMessage: string | null;
}) {
  if (loadState === "error") {
    return (
      <section className="notice error" role="alert">
        <strong>{bilingualLabel("算法清单暂时不可用", "Algorithm registry unavailable")}</strong>
        <span>{errorMessage}</span>
      </section>
    );
  }

  if (algorithms === null) {
    return (
      <section className="notice">
        <strong>{bilingualLabel("正在读取算法清单", "Loading algorithm registry")}</strong>
        <span>{bilingualLabel("连接 quant_ops_api", "Connecting to quant_ops_api")}</span>
      </section>
    );
  }

  const availableCount = algorithms.filter((algorithm) => algorithm.status === "available").length;
  const plannedCount = algorithms.filter((algorithm) => algorithm.status === "planned").length;
  const outputKinds = Array.from(
    new Set(algorithms.flatMap((algorithm) => algorithm.capability.output_kinds)),
  );

  return (
    <>
      <section className="validation-hero">
        <div>
          <p className="eyebrow">{bilingualLabel("因子实验室", "Factor Lab")}</p>
          <h3>{bilingualLabel("算法注册表", "Algorithm Registry")}</h3>
          <span className="muted">quant_factor_lab</span>
        </div>
        <div className="decision-block">
          <span>{bilingualLabel("可运行算法", "Available Algorithms")}</span>
          <strong>{availableCount}</strong>
        </div>
        <div className="metric-grid compact">
          <MetricTile label={bilingualLabel("算法数", "Algorithms")} value={String(algorithms.length)} />
          <MetricTile label={bilingualLabel("候选数", "Planned")} value={String(plannedCount)} />
          <MetricTile label={bilingualLabel("输出类型", "Output Kinds")} value={String(outputKinds.length)} />
          <MetricTile label={bilingualLabel("主库", "Primary Library")} value={resolvePrimaryAlgorithmLibrary(algorithms)} />
        </div>
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("算法适配器", "Algorithm Adapters")}</p>
            <h3>{bilingualLabel("算法适配清单", "Adapter Registry")}</h3>
          </div>
          <span className="muted">{availableCount} available / {plannedCount} planned</span>
        </div>
        <div className="algorithm-grid">
          {algorithms.map((algorithm) => (
            <AlgorithmCard algorithm={algorithm} key={algorithm.algorithm_id} />
          ))}
        </div>
      </section>
    </>
  );
}

function AlgorithmCard({ algorithm }: { algorithm: AlgorithmSpec }) {
  const parameters = algorithm.parameters.map((parameter) => (
    <span key={parameter.name}>
      {parameter.name}={formatAlgorithmParameterDefault(parameter.default_value)}
    </span>
  ));
  const notes = [...algorithm.research_notes, ...algorithm.limitations];
  const requiredReviewGateCount = algorithm.review_gates.filter((gate) => gate.is_required).length;
  const missingRequiredReviewGateCount = algorithm.review_gates.filter(
    (gate) => gate.is_required && gate.status === "missing",
  ).length;

  return (
    <article className="algorithm-card">
      <div className="algorithm-card-heading">
        <div>
          <p className="eyebrow">{algorithm.role}</p>
          <h4>{algorithm.display_name}</h4>
          <span>{algorithm.algorithm_id}</span>
        </div>
        <span className={`status-pill ${resolveAlgorithmStatusPillClass(algorithm.status)}`}>
          {ALGORITHM_STATUS_LABELS[algorithm.status] ?? algorithm.status}
        </span>
      </div>

      <p className="algorithm-description">{algorithm.description}</p>

      <div className="algorithm-meta-grid">
        <MetricTile label={bilingualLabel("版本", "Version")} value={algorithm.version} />
        <MetricTile label={bilingualLabel("库", "Library")} value={algorithm.source_library ?? "internal"} />
        <MetricTile label={bilingualLabel("资产", "Assets")} value={formatShortList(algorithm.capability.asset_classes)} />
        <MetricTile label={bilingualLabel("模式", "Modes")} value={formatShortList(algorithm.capability.factor_modes)} />
      </div>

      <div className="source-strip">
        <span>{formatShortList(algorithm.capability.factor_families)}</span>
        <span>{formatShortList(algorithm.capability.output_kinds)}</span>
        <span>{formatShortList(algorithm.capability.timeframes)}</span>
        <span>{algorithm.adapter_module ?? "pending_adapter"}</span>
      </div>

      {algorithm.review_gates.length > 0 ? (
        <div className="algorithm-readiness">
          <div>
            <span>{bilingualLabel("准入门槛", "Review Gates")}</span>
            <strong>
              {requiredReviewGateCount - missingRequiredReviewGateCount}/{requiredReviewGateCount}
            </strong>
          </div>
          <span className={`status-pill ${missingRequiredReviewGateCount === 0 ? "pill-ok" : "pill-degraded"}`}>
            {resolveAlgorithmReadinessLabel({
              algorithmStatus: algorithm.status,
              missingRequiredReviewGateCount,
            })}
          </span>
        </div>
      ) : null}

      {algorithm.review_gates.length > 0 ? (
        <AlgorithmReviewGateList gates={algorithm.review_gates} />
      ) : null}

      {parameters.length > 0 ? <div className="tag-list">{parameters}</div> : null}
      {algorithm.tags.length > 0 ? (
        <div className="tag-list">
          {algorithm.tags.map((tag) => (
            <span key={tag}>{tag}</span>
          ))}
        </div>
      ) : null}
      {notes.length > 0 ? (
        <div className="finding-list">
          {notes.slice(0, 3).map((note) => (
            <div className="finding-item severity-info" key={note}>
              <strong>review_note</strong>
              <span>{note}</span>
            </div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

function AlgorithmReviewGateList({ gates }: { gates: AlgorithmReviewGate[] }) {
  return (
    <div className="review-gate-list">
      {gates.map((gate) => (
        <div className={`review-gate ${resolveReviewGateClass(gate.status)}`} key={gate.gate_id}>
          <div>
            <strong>{resolveReviewGateTitle(gate)}</strong>
            <span>{resolveReviewGateCategory(gate)}</span>
          </div>
          <span className="review-gate-status">
            {ALGORITHM_REVIEW_GATE_STATUS_LABELS[gate.status] ?? gate.status}
          </span>
          <p>{resolveReviewGateBody(gate)}</p>
        </div>
      ))}
    </div>
  );
}

function FactorValidationReviewPanel({
  review,
  loadState,
  errorMessage,
  comparisonPreview,
  comparisonLoadState,
  comparisonErrorMessage,
  onRunComparison,
}: {
  review: FactorValidationReviewResponse | null;
  loadState: LoadState;
  errorMessage: string | null;
  comparisonPreview: ExternalPayloadComparisonPreviewResponse | null;
  comparisonLoadState: LoadState;
  comparisonErrorMessage: string | null;
  onRunComparison: () => void;
}) {
  if (loadState === "error") {
    return (
      <section className="notice error" role="alert">
        <strong>{bilingualLabel("因子验证审核摘要暂时不可用", "Factor validation review unavailable")}</strong>
        <span>{errorMessage}</span>
      </section>
    );
  }

  if (review === null) {
    return (
      <section className="notice">
        <strong>{bilingualLabel("正在读取因子验证审核摘要", "Loading factor validation review")}</strong>
        <span>{bilingualLabel("连接 quant_ops_api", "Connecting to quant_ops_api")}</span>
      </section>
    );
  }

  const metric = review.latest_metric;

  return (
    <>
      <section className={`validation-hero decision-${metric.decision}`}>
        <div>
          <p className="eyebrow">{bilingualLabel("因子验证", "Factor Validation")}</p>
          <h3>{metric.factor_name}</h3>
          <span className="muted">{metric.run_id}</span>
        </div>
        <div className="decision-block">
          <span>{bilingualLabel("审核状态", "Review Status")}</span>
          <strong>{DECISION_LABELS[metric.decision]}</strong>
        </div>
        <div className="metric-grid compact">
          <MetricTile label={bilingualLabel("样本", "Samples")} value={`${metric.effective_sample_count}/${metric.sample_count}`} />
          <MetricTile label={bilingualLabel("覆盖率", "Coverage")} value={formatRatio(metric.coverage_ratio)} />
          <MetricTile label="IC" value={formatNumber(metric.ic_mean)} />
          <MetricTile label="Rank IC" value={formatNumber(metric.rank_ic_mean)} />
          <MetricTile label={bilingualLabel("分组数", "Groups")} value={String(metric.group_count)} />
          <MetricTile label={bilingualLabel("分组差", "Group Spread")} value={formatNumber(metric.group_return_spread_mean)} />
        </div>
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
              <p className="eyebrow">{bilingualLabel("审核发现", "Review Findings")}</p>
              <h3>{bilingualLabel("审核发现", "Findings")}</h3>
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

      {review.score_card !== null ? (
        <section className="service-panel">
          <div className="section-heading">
            <div>
              <p className="eyebrow">{bilingualLabel("第一阶段评分", "First-Stage Score")}</p>
              <h3>{formatNumber(review.score_card.final_score)} / {review.score_card.max_score}</h3>
            </div>
            <span className="status-pill pill-ok">{review.score_card.evaluation_engine}</span>
          </div>
          {review.comparison !== null ? (
            <div className="metric-grid compact">
              <MetricTile label={bilingualLabel("引擎数", "Engines")} value={String(review.comparison.engine_count)} />
              <MetricTile
                label={bilingualLabel("分歧", "Disagreement")}
                value={review.comparison.has_engine_disagreement ? "yes" : "no"}
              />
              <MetricTile label={bilingualLabel("主引擎", "Primary Engine")} value={review.comparison.primary_engine} />
            </div>
          ) : null}
          <div className="finding-list">
            {review.score_card.score_components.map((component) => (
              <div className="finding-item severity-info" key={component.name}>
                <strong>{component.name}: {formatNumber(component.score)}</strong>
                <span>{component.reason}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <ExternalPayloadComparisonPanel
        errorMessage={comparisonErrorMessage}
        loadState={comparisonLoadState}
        onRunComparison={onRunComparison}
        preview={comparisonPreview}
      />

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("Manifest 预览", "Manifest Preview")}</p>
            <h3>{review.manifest.manifest_id}</h3>
          </div>
          <span className="muted">{formatDateTime(review.generated_at)}</span>
        </div>
        <ArtifactTable artifacts={review.manifest.artifacts} />
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("后续审核动作", "Next Review Actions")}</p>
            <h3>{bilingualLabel("后续动作", "Next Actions")}</h3>
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

function ExternalPayloadComparisonPanel({
  preview,
  loadState,
  errorMessage,
  onRunComparison,
}: {
  preview: ExternalPayloadComparisonPreviewResponse | null;
  loadState: LoadState;
  errorMessage: string | null;
  onRunComparison: () => void;
}) {
  const report = preview?.comparison_report ?? null;
  const artifactReference = preview?.artifact_reference ?? null;
  const limitations = preview?.limitations ?? [];

  return (
    <section className="service-panel">
      <div className="section-heading">
        <div>
          <p className="eyebrow">{bilingualLabel("外部引擎", "External Engines")}</p>
          <h3>{bilingualLabel("多引擎 payload 对比", "Multi-Engine Payload Comparison")}</h3>
        </div>
        <button
          className="inline-action"
          disabled={loadState === "loading"}
          type="button"
          onClick={onRunComparison}
        >
          {loadState === "loading" ? bilingualLabel("对比中", "Comparing") : bilingualLabel("重新对比", "Compare Again")}
        </button>
      </div>

      {preview !== null ? (
        <div className="source-strip">
          <span>{preview.source}</span>
          <span>{preview.artifact_read_status}</span>
          <span>{preview.artifact_read_reason ?? "no_reason"}</span>
          <span>{formatDateTime(preview.generated_at)}</span>
        </div>
      ) : null}

      {artifactReference !== null ? (
        <div className="source-strip">
          <span>{artifactReference.artifact_id}</span>
          <span>{artifactReference.schema_version ?? "unknown_schema"}</span>
          <span>{artifactReference.storage_type}</span>
          <span>{artifactReference.object_key ?? artifactReference.uri ?? artifactReference.task_id}</span>
        </div>
      ) : null}

      {loadState === "error" ? (
        <div className="notice error" role="alert">
          <strong>{bilingualLabel("外部 payload 对比暂时不可用", "External payload comparison unavailable")}</strong>
          <span>{errorMessage}</span>
        </div>
      ) : null}

      {report === null && loadState !== "error" ? (
        <div className="empty-state">
          <strong>{bilingualLabel("等待对比结果", "Waiting for comparison result")}</strong>
          <span>{bilingualLabel("连接 quant_ops_api", "Connecting to quant_ops_api")}</span>
        </div>
      ) : null}

      {report !== null ? (
        <>
          <div className="comparison-ribbon">
            <MetricTile label={bilingualLabel("因子", "Factor")} value={report.factor_name} />
            <MetricTile label={bilingualLabel("主引擎", "Primary Engine")} value={report.primary_engine} />
            <MetricTile label={bilingualLabel("引擎数", "Engines")} value={String(report.engine_count)} />
            <MetricTile label={bilingualLabel("分歧", "Disagreement")} value={report.has_engine_disagreement ? "yes" : "no"} />
          </div>
          <div className="engine-matrix">
            {report.engine_results.map((result) => (
              <EngineResultCard result={result} key={result.evaluation_engine} />
            ))}
          </div>
          <div className="finding-item severity-info">
            <strong>comparison_summary</strong>
            <span>{report.comparison_summary}</span>
          </div>
          {limitations.length > 0 ? (
            <div className="action-list">
              {limitations.map((limitation) => (
                <span key={limitation}>{limitation}</span>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function EngineResultCard({ result }: { result: FactorEvaluationResult }) {
  const decision = resolveEngineDecision(result);

  return (
    <article className="engine-card">
      <div className="engine-card-heading">
        <strong>{result.evaluation_engine}</strong>
        <span className={`status-pill ${resolveDecisionPillClass(decision)}`}>
          {DECISION_LABELS[decision]}
        </span>
      </div>
      <div className="engine-metrics">
        <MetricTile label={bilingualLabel("评分", "Score")} value={formatNumber(result.score_card?.final_score)} />
        <MetricTile label="IC" value={formatNumber(result.metrics.ic_mean)} />
        <MetricTile label="Rank IC" value={formatNumber(result.metrics.rank_ic_mean)} />
        <MetricTile label={bilingualLabel("分组差", "Spread")} value={formatNumber(result.metrics.group_return_spread_mean)} />
        <MetricTile label={bilingualLabel("覆盖率", "Coverage")} value={formatRatio(result.metrics.coverage_ratio)} />
        <MetricTile label={bilingualLabel("样本", "Sample")} value={`${result.metrics.effective_sample_count}/${result.metrics.sample_count}`} />
      </div>
    </article>
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
        <strong>{bilingualLabel("暂无产物", "No Artifacts")}</strong>
        <span>{bilingualLabel("等待 manifest 返回 artifact 列表。", "Waiting for manifest artifact list.")}</span>
      </div>
    );
  }

  return (
    <div className="artifact-table">
      <div className="artifact-row header">
        <span>{bilingualLabel("类型", "Type")}</span>
        <span>Schema</span>
        <span>{bilingualLabel("对象键", "Object Key")}</span>
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

function ArtifactLedgerPanel({
  ledger,
  loadState,
  errorMessage,
}: {
  ledger: ArtifactLedgerResponse | null;
  loadState: LoadState;
  errorMessage: string | null;
}) {
  if (loadState === "error") {
    return (
      <section className="notice error" role="alert">
        <strong>{bilingualLabel("Artifact ledger 暂时不可用", "Artifact ledger unavailable")}</strong>
        <span>{errorMessage}</span>
      </section>
    );
  }

  if (ledger === null) {
    return (
      <section className="notice">
        <strong>{bilingualLabel("正在读取任务与产物账本", "Loading task and artifact ledger")}</strong>
        <span>{bilingualLabel("连接 quant_ops_api", "Connecting to quant_ops_api")}</span>
      </section>
    );
  }

  return (
    <>
      <section className="validation-hero">
        <div>
          <p className="eyebrow">{bilingualLabel("任务产物账本", "Task Artifact Ledger")}</p>
          <h3>{ledger.source}</h3>
          <span className="muted">{formatDateTime(ledger.generated_at)}</span>
        </div>
        <div className="decision-block">
          <span>{bilingualLabel("持久化状态", "Persistence Status")}</span>
          <strong>{ledger.persistence_status}</strong>
        </div>
        <div className="metric-grid compact">
          <MetricTile label={bilingualLabel("任务数", "Tasks")} value={String(ledger.task_count)} />
          <MetricTile label={bilingualLabel("产物数", "Artifacts")} value={String(ledger.artifact_count)} />
          <MetricTile label={bilingualLabel("任务类型", "Task Type")} value={ledger.tasks[0]?.task_type ?? "--"} />
          <MetricTile label={bilingualLabel("存储类型", "Storage")} value={ledger.artifacts[0]?.storage_type ?? "--"} />
        </div>
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("任务运行", "Task Runs")}</p>
            <h3>{bilingualLabel("任务账本", "Task Ledger")}</h3>
          </div>
          <span className="status-pill pill-degraded">{ledger.persistence_status}</span>
        </div>
        <TaskLedgerTable ledger={ledger} />
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("任务产物", "Task Artifacts")}</p>
            <h3>{bilingualLabel("产物账本", "Artifact Ledger")}</h3>
          </div>
        </div>
        <ArtifactLedgerTable artifacts={ledger.artifacts} />
      </section>

      <section className="service-panel">
        <div className="section-heading">
          <div>
            <p className="eyebrow">{bilingualLabel("账本边界", "Ledger Limitations")}</p>
            <h3>{bilingualLabel("接入边界", "Integration Boundaries")}</h3>
          </div>
        </div>
        <div className="action-list">
          {ledger.limitations.map((limitation) => (
            <span key={limitation}>{limitation}</span>
          ))}
        </div>
      </section>
    </>
  );
}

function TaskLedgerTable({ ledger }: { ledger: ArtifactLedgerResponse }) {
  if (ledger.tasks.length === 0) {
    return (
      <div className="empty-state">
        <strong>{bilingualLabel("暂无任务", "No Tasks")}</strong>
        <span>{bilingualLabel("等待 task_runs 只读视图返回任务。", "Waiting for the task_runs read-only view.")}</span>
      </div>
    );
  }

  return (
    <div className="artifact-table">
      <div className="task-row header">
        <span>{bilingualLabel("任务", "Task")}</span>
        <span>{bilingualLabel("状态", "Status")}</span>
        <span>{bilingualLabel("产物数", "Artifacts")}</span>
        <span>{bilingualLabel("完成时间", "Finished At")}</span>
      </div>
      {ledger.tasks.map((task) => (
        <div className="task-row" key={task.task_id}>
          <div>
            <strong>{task.task_name}</strong>
            <span>{task.task_id}</span>
          </div>
          <span className="status-pill pill-ok">{task.status}</span>
          <span>{task.artifact_count}</span>
          <span>{task.finished_at ? formatDateTime(task.finished_at) : "--"}</span>
        </div>
      ))}
    </div>
  );
}

function ArtifactLedgerTable({ artifacts }: { artifacts: ArtifactLedgerItem[] }) {
  if (artifacts.length === 0) {
    return (
      <div className="empty-state">
        <strong>{bilingualLabel("暂无产物", "No Artifacts")}</strong>
        <span>{bilingualLabel("等待 task_artifacts 只读视图返回产物。", "Waiting for the task_artifacts read-only view.")}</span>
      </div>
    );
  }

  return (
    <div className="artifact-table">
      <div className="artifact-row header">
        <span>{bilingualLabel("类型", "Type")}</span>
        <span>{bilingualLabel("存储", "Storage")}</span>
        <span>{bilingualLabel("对象键", "Object Key")}</span>
      </div>
      {artifacts.map((artifact) => (
        <div className="artifact-row" key={artifact.artifact_id}>
          <strong>{artifact.artifact_type}</strong>
          <span>{artifact.storage_type}</span>
          <span>{artifact.object_key ?? artifact.uri ?? "--"}</span>
        </div>
      ))}
    </div>
  );
}

function resolveRefreshHandler({
  activeView,
  loadArtifactLedger,
  loadFactorAlgorithms,
  loadExternalPayloadComparison,
  loadFactorValidationReview,
  loadOverview,
}: {
  activeView: DashboardView;
  loadArtifactLedger: () => void;
  loadFactorAlgorithms: () => void;
  loadExternalPayloadComparison: () => void;
  loadFactorValidationReview: () => void;
  loadOverview: () => void;
}) {
  if (activeView === "overview") return loadOverview;
  if (activeView === "factor-lab") return loadFactorAlgorithms;
  if (activeView === "factor-validation") {
    return () => {
      loadFactorValidationReview();
      loadExternalPayloadComparison();
    };
  }
  return loadArtifactLedger;
}

function resolvePageTitle(activeView: DashboardView): string {
  if (activeView === "overview") return bilingualLabel("核心量化服务状态", "Core Quant Service Status");
  if (activeView === "factor-lab") return bilingualLabel("因子算法适配清单", "Factor Algorithm Adapters");
  if (activeView === "factor-validation") return bilingualLabel("因子验证审核视图", "Factor Validation Review");
  return bilingualLabel("任务与产物账本", "Task and Artifact Ledger");
}

function resolveOverviewLabel(status: ServiceStatus): string {
  if (status === "ok") return bilingualLabel("主链路健康", "Main Pipeline Healthy");
  if (status === "degraded") return bilingualLabel("部分服务需关注", "Some Services Need Attention");
  return bilingualLabel("主链路不可用", "Main Pipeline Unavailable");
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
  if (value === null || value === undefined) return "--";
  return `${(value * 100).toFixed(1)}%`;
}

function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "--";
  return value.toFixed(3);
}

function formatShortList(values: string[]): string {
  if (values.length === 0) return "--";
  if (values.length <= 2) return values.join(" / ");
  return `${values.slice(0, 2).join(" / ")} +${values.length - 2}`;
}

function formatAlgorithmParameterDefault(value: number | string | boolean | null): string {
  if (value === null) return "unset";
  if (typeof value === "boolean") return value ? "true" : "false";
  return String(value);
}

function resolvePrimaryAlgorithmLibrary(algorithms: AlgorithmSpec[]): string {
  const firstExternalLibrary = algorithms.find((algorithm) => algorithm.source_library !== null);
  return firstExternalLibrary?.source_library ?? "internal";
}

function resolveEngineDecision(result: FactorEvaluationResult): ValidationDecision {
  if (result.report !== null) return result.report.decision;
  if (result.score_card !== null) return result.score_card.review_decision;
  return "review_required";
}

function resolveDecisionPillClass(decision: ValidationDecision): string {
  if (decision === "candidate_pass") return "pill-ok";
  if (decision === "review_required") return "pill-degraded";
  return "pill-down";
}

function resolveAlgorithmStatusPillClass(status: string): string {
  if (status === "available") return "pill-ok";
  if (status === "planned") return "pill-degraded";
  return "pill-down";
}

function resolveAlgorithmReadinessLabel({
  algorithmStatus,
  missingRequiredReviewGateCount,
}: {
  algorithmStatus: string;
  missingRequiredReviewGateCount: number;
}): string {
  if (missingRequiredReviewGateCount > 0) {
    return bilingualLabel(`${missingRequiredReviewGateCount} 项待补`, `${missingRequiredReviewGateCount} Missing`);
  }
  if (algorithmStatus === "planned") return bilingualLabel("可升级", "Ready to Promote");
  return bilingualLabel("已满足", "Ready");
}

function resolveReviewGateClass(status: string): string {
  if (status === "satisfied") return "review-gate-ok";
  if (status === "missing") return "review-gate-warning";
  return "review-gate-muted";
}

function resolveReviewGateTitle(gate: AlgorithmReviewGate): string {
  return ALGORITHM_REVIEW_GATE_TITLE_LABELS[gate.gate_id] ?? gate.title;
}

function resolveReviewGateCategory(gate: AlgorithmReviewGate): string {
  return ALGORITHM_REVIEW_GATE_CATEGORY_LABELS[gate.category] ?? gate.category;
}

function resolveReviewGateBody(gate: AlgorithmReviewGate): string {
  return ALGORITHM_REVIEW_GATE_BODY_LABELS[gate.gate_id] ?? gate.evidence ?? gate.description;
}

function bilingualLabel(chineseText: string, englishText: string): string {
  return `${chineseText} / ${englishText}`;
}
