# Web UI 与监控需求

> 目标：让当前项目像 101 节点已有 Web UI 一样，具备统一展示、运行监控、任务血缘和研究产物查看能力。但 Web UI 只能作为观测与运营入口，不能破坏各服务独立边界。

---

## 1. 结论

当前项目应新增一个独立应用：

```text
apps/quant_ops_web
services/quant_ops_api
```

定位：

```text
quant_ops_web = 只读优先的运营 Dashboard / Monitoring UI
quant_ops_api = 只读优先的运营聚合 API / BFF
```

它们不替代 `quant_data_hub`、`quant_factor_lab`、`quant_factor_validation`，也不直接承担数据接入、因子计算或因子验证逻辑。

当前已落地第一版 Overview、Factor Lab、Factor Validation 与 Artifacts 页面：

```text
GET /api/v1/overview
GET /api/v1/factor-validation/review
GET /api/v1/factor-validation/external-payloads/preview
POST /api/v1/factor-validation/external-payloads/compare
GET /api/v1/artifacts/ledger
```

`quant_ops_web` 通过 `/ops-api` 代理读取 `quant_ops_api`，展示整体状态、服务健康表、Factor Lab algorithm registry、review gates、因子验证 decision、IC / Rank IC 摘要、findings、manifest artifact preview、Alphalens / Qlib / vectorbt payload 对比结果、`factor_comparison_report.v1` 产物引用或对象内容读取结果、artifact 读取状态，以及任务/产物账本预览。当前主要页面文案采用“中文 / English”并存显示，便于研究员、工程和运维协作。

---

## 2. 第一版范围

MVP 阶段先做只读展示：

```text
服务健康状态
数据源连接状态
最近任务运行记录
最近产物 manifest
因子计算运行摘要
因子验证报告列表
101 节点只读 smoke test 状态
```

第一版不做：

```text
在线编辑生产配置
直接执行危险重算
直接写 ClickHouse / PostgreSQL / MinIO
展示大规模行情明细
绕过后端 API 访问数据库
替代 Prometheus / Grafana
```

---

## 3. 数据来源

`quant_ops_web` 只能通过明确接口读取数据：

```text
quant_data_hub HTTP API
quant_factor_lab HTTP API
quant_factor_validation HTTP API
quant_ops_api HTTP API
后续 task/artifact API
MinIO 中的 manifest / latest.json 只读对象
101 节点只读巡检 API 或 smoke test 输出
```

允许读取 101 节点已有的历史经验与产物结构，例如：

```text
custom/dashboard_latest-*/latest.json
custom/manifest-*/manifest.json
factor-metrics/*/metrics.json
```

但这些结构进入当前项目时，必须先映射成 `quant_contracts` 或当前应用自己的 Pydantic 只读模型。

---

## 4. 架构约束

- Web UI 不直接 import 业务服务内部 `repository`、`service`、`model`。
- Web UI 不直接连接生产数据库；如需数据库信息，必须通过后端只读 API 或只读视图。
- Web UI 默认只读；任何写操作必须有单独 API、权限校验、审计日志和确认流程。
- Web UI 不能保存真实 token、password、access key。
- Web UI 不能默认拉取大规模行情数据到浏览器。
- UI 展示的状态必须带时间戳、来源服务、数据版本或 run_id。
- 主要导航、页面标题、按钮、表头、状态、空状态和关键指标标签必须采用“中文 / English”并存显示；接口字段名、算法 ID、run_id、schema version、object key 等技术标识保持原值。
- 监控告警不能只依赖前端轮询，生产阶段应接入日志、指标和告警系统。

---

## 5. 推荐页面

第一版页面：

```text
Overview
  服务健康、最近运行、关键告警

Data Hub
  ClickHouse 连接、行情数据区间、qfq 批次、最近 smoke test

Factor Lab
  因子计算 run_id、factor_name、样本区间、行数、状态

Factor Validation
  验证报告、decision、findings、IC / Rank IC、分组收益摘要、多引擎 payload 对比、manifest preview、报告产物链接

Artifacts
  manifest preview、MinIO persisted manifest、latest.json、报告文件索引

System
  版本、配置摘要、容器状态、只读巡检结果
```

---

## 6. 技术建议

前端可以使用：

```text
React + TypeScript + Vite
```

后端聚合层可以二选一：

```text
方案 A：前端直接调用各服务 HTTP API
方案 B：增加轻量 BFF/API gateway，聚合各服务只读状态
```

MVP 推荐方案 B：

```text
apps/quant_ops_web      # 前端 UI
services/quant_ops_api  # 只读聚合 API，当前已落地 overview、factor-validation review、external payload preview/compare 和 artifact ledger
```

短期本地开发优先让 `quant_ops_web` 调用 `quant_ops_api`，只有调试单服务时才直接调用业务服务只读接口。

本地容器入口：

```bash
make quant-ops-web-up
make quant-ops-web-check
```

默认地址：

```text
http://127.0.0.1:18040
```

---

## 7. 与 MVP 主线关系

主线仍然是：

```text
quant_contracts
  ↓
quant_data_hub
  ↓
quant_data_sdk
  ↓
quant_factor_lab
  ↓
quant_factor_validation
```

`quant_ops_web` 是旁路观测层：

```text
quant_ops_web
  ↓
quant_ops_api
  ├── 读取 quant_data_hub 状态
  ├── 读取 quant_factor_lab 状态
  ├── 读取 quant_factor_validation 报告
  ├── 代理 quant_factor_validation 外部 payload 对比
  └── 读取 artifact / manifest / task ledger 索引
```

它们可以从第一版开始预留目录和约束，但不应阻塞核心数据、因子和验证闭环。

当前 Artifacts 页通过 `/api/v1/artifacts/ledger` 获取账本。未配置账本数据库时，接口返回 `not_persisted` manifest preview，用来固定 task/artifact 展示协议；配置 `ARTIFACT_LEDGER_DATABASE_URL` 或 `VALIDATION_DATABASE_URL` 后，`quant_ops_api` 会只读查询 PostgreSQL `task_runs` / `task_artifacts`。复用 101 旧库时必须配置 `ARTIFACT_LEDGER_DATABASE_SCHEMA` 或 `VALIDATION_DATABASE_SCHEMA`，避免读取 public schema 下 UUID 版旧表。当前 manifest 已包含 `file_size_bytes`、`content_type` 和 `sha256`，页面应优先展示这些字段，帮助研究员确认产物完整性。Web UI 不应直接持有数据库写权限或 MinIO access key。

Factor Lab 页面通过 `quant_ops_api` 读取 `quant_factor_lab` 的 algorithm review evidence list。页面只展示每个 review gate 的证据数量、最近 evidence source、提交人和提交时间；证据写入由 `quant_factor_lab` 的 `POST /api/v1/algorithms/review-gates/evidence` 完成，Web UI 不直接持有数据库写权限。gate 状态仍由后续显式 review decision 更新，不能因为存在 evidence record 自动升级为 satisfied。
