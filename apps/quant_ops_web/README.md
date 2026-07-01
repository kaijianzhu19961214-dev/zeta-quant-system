# quant_ops_web / 运营监控 Web UI

`quant_ops_web` 是当前项目的运营 Dashboard 和监控入口，用于展示服务状态、任务运行、数据产物、因子计算和因子验证结果。

## 职责

- 展示 `quant_data_hub`、`quant_factor_lab`、`quant_factor_validation` 的健康状态。
- 展示任务运行、run_id、数据版本、产物 manifest 和报告索引。
- 展示 101 节点只读 smoke test 或巡检结果。
- 为后续生产监控、告警和审计提供统一入口。

## 不做什么

- 不直接连接生产数据库。
- 不直接写 ClickHouse / PostgreSQL / MinIO。
- 不执行未审计的重算、删除或生产配置修改。
- 不替代核心服务 API。
- 不拉取大规模行情明细到浏览器。

## MVP 页面

```text
Overview
Data Hub
Factor Lab
Factor Validation
Artifacts
System
```

## 当前状态

当前已落地 MVP 页面：

- 通过 Vite 代理 `/ops-api` 读取 `quant_ops_api /api/v1/overview`。
- 展示整体状态、最后刷新时间、健康服务数量、异常服务数量。
- 展示 `quant_data_hub`、`quant_factor_lab`、`quant_factor_validation` 的状态表。
- 通过 `quant_ops_api /api/v1/factor-validation/review` 展示因子验证审核摘要。
- 展示 `decision`、IC / Rank IC、分组收益差、findings、recommended actions 和 manifest artifact preview。
- 通过 `quant_ops_api /api/v1/factor-validation/external-payloads/preview` 展示 Alphalens / Qlib / vectorbt payload 的统一 `FactorComparisonReport` 预览，并展示对应 `factor_comparison_report.v1` 产物引用。
- 通过 `quant_ops_api /api/v1/artifacts/ledger` 展示任务账本和产物账本预览。
- 提供加载、刷新和错误态，保持只读边界。

当前 Factor Validation 页仍是 `not_persisted` 预览，不表示报告已经入库或上传 MinIO。

当前外部引擎对比区优先展示 `artifact_reference` 指向的标准 `comparison_report.json`；当对象存储未配置、读取失败或 payload 校验失败时，回退读取 BFF 提供的 MVP 预览结果，用于验证 UI -> BFF -> `quant_factor_validation` 链路。页面会展示 `artifact_read_status` 和 `artifact_read_reason`，用于区分 `artifact_loaded` 与 `preview_fallback`。后续接入真实研究任务后，应继续通过只读 object-store adapter 读取标准 artifact 或研究员提交的已审核 payload。

当前 Artifacts 页同样是 `not_persisted` 预览：它展示的是由因子验证 manifest 映射出的 task/artifact ledger 形态，用于提前固定 Web UI 和 API 协议。后续接入 101 节点 PostgreSQL `task_runs` / `task_artifacts` 或 MinIO `latest.json` 后，才能作为正式产物账本使用。

## 本地运行

```bash
make quant-ops-web-up
make quant-ops-web-check
```

默认访问地址：

```text
http://127.0.0.1:18040
```

## 本地验证

```bash
make test-quant-ops-web
make quant-ops-web-build
```
