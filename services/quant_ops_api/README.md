# quant_ops_api / 运营聚合 API

`quant_ops_api` 是只读运营聚合层，为后续 `quant_ops_web` 提供统一状态接口。

`quant_ops_api` is a read-only operations API for the future dashboard.

## 职责 / Responsibilities

- 聚合核心服务健康状态。
- 给 Web UI 提供稳定只读 API。
- 隔离前端与各业务服务的内部实现。
- 保留后续 task / artifact / manifest 查询入口。

## 当前 MVP / Current MVP

当前已落地：

```text
GET /health
GET /api/v1/overview
GET /api/v1/market-data/price-modes
GET /api/v1/market-data/source-coverage
GET /api/v1/market-data/ingestion-ledger/preview
POST /api/v1/market-data/bars/sample
GET /api/v1/factor-lab/algorithms
GET /api/v1/factor-lab/factors/samples/momentum-1d
GET /api/v1/factor-validation/review
GET /api/v1/factor-validation/external-payloads/preview
POST /api/v1/factor-validation/external-payloads/compare
GET /api/v1/artifacts/ledger
```

`/api/v1/overview` 当前聚合：

```text
quant_data_hub
quant_factor_lab
quant_factor_validation
```

返回内容：

```text
status
generated_at
services[]
service_count
healthy_count
degraded_count
down_count
```

`/api/v1/market-data/price-modes` 当前只读聚合 `quant_data_hub /api/v1/adjustments/qfq-batches`，输出 raw / qfq / hfq 三种价格口径、ClickHouse 存储对象、是否需要 `batch_id`、最新 qfq batch 和 `qfq_base_date`。该接口用于 Web UI 监控因子计算前的数据口径，不直接查询大规模行情明细。

`/api/v1/market-data/source-coverage` 当前只读聚合 `quant_data_hub /api/v1/market-data/source-coverage`，输出 ClickHouse raw 行情表按 `timeframe / dataset_code / source_name` 的行数、标的数、交易日数、日期范围和重复键行数。同时返回 PostgreSQL / ClickHouse / MinIO / Redis 的存储职责说明：ClickHouse 是行情明细主查询库，PostgreSQL 只保存任务、批次、血缘和质量检查，MinIO 保存原始响应、Parquet 快照和产物归档，Redis 只做缓存和短期状态。

`/api/v1/market-data/ingestion-ledger/preview` 当前只读聚合 `quant_data_hub /api/v1/ingestion/ledger/preview`，把 ClickHouse source coverage 派生的导入批次、质量检查和 `persistence_status` 暴露给 Web UI。该接口用于验证 PostgreSQL 控制面账本协议，不写 PostgreSQL、ClickHouse 或 MinIO；正式落库后仍由 `quant_data_hub` 在导入任务完成时写控制面表。

`/api/v1/market-data/bars/sample` 是受控小样本预览接口：请求体采用 `MarketDataBarsSampleRequest`，由 `quant_ops_api` 转发到 `quant_data_hub /api/v1/market-bars/query`，响应返回 `MarketDataBarsSampleResponse`，其中 `meta` 和 `rows` 复用 `quant_contracts.MarketBarsResponse` 的标准结构。当前 Web UI 默认请求 `000001.SZ / 1d / raw / 2026-06-10`，接口限制 `limit <= 20`；当 `price_mode=qfq` 且未传 `batch_id` 时，BFF 会读取最新 qfq batch 后再查询。该接口只用于 UI smoke 和数据口径确认，不替代正式因子任务的数据读取接口。

`/api/v1/factor-lab/algorithms` 是 Factor Lab 算法 registry 的只读 BFF 代理接口：由 `quant_ops_api` 转发读取 `quant_factor_lab /api/v1/algorithms`，响应复用 `quant_contracts.AlgorithmSpec[]`。该接口只展示 `available` / `planned` 算法能力、参数、来源库、状态和 `review_gates` 准入门槛，不直接安装第三方库，不执行候选算法，也不绕过 `quant_factor_lab` 的 adapter registry。

`/api/v1/factor-lab/factors/samples/momentum-1d` 是受控真实因子样本接口：由 `quant_ops_api` 固定构造 `momentum_1d / technical.momentum / 000001.SZ / 2026-06-09~2026-06-10 / raw` 请求，并转发到 `quant_factor_lab /api/v1/factors/calculate`。响应复用 `quant_contracts.FactorCalculationResponse`。该接口只用于 Web UI smoke，证明 UI -> BFF -> `quant_factor_lab` -> `quant_data_hub` -> ClickHouse -> factor adapter 的真实链路，不提供任意研究参数，也不持久化结果。

`/api/v1/factor-validation/review` 当前返回：

```text
latest_metric
findings
recommended_actions
manifest
limitations
```

该接口只暴露因子验证审核摘要和 manifest preview。当前 `latest_metric` 包含 IC、Rank IC、分组数和高低分组收益差均值；manifest preview 已扩展为 6 类产物：

```text
validation_report.json
metrics.json
ic_series.json
group_returns.json
score_card.json
comparison_report.json
```

`/api/v1/factor-validation/external-payloads/preview` 是 Web UI 使用的只读预览接口：优先通过 `artifact_reference` 读取 `factor_comparison_report.v1` 标准产物；未配置对象存储、读取失败或 payload 校验失败时，回退到 `quant_ops_api` 构造的 MVP 预览 payload，并代理到 `quant_factor_validation /api/v1/factors/external-payloads/compare`。响应包含 `source`、`generated_at`、`comparison_report`、`artifact_reference`、`artifact_read_status`、`artifact_read_reason`、`artifact_read_message` 和 `limitations`，其中 `comparison_report` 复用 `quant_contracts.FactorComparisonReport`。该接口用于固定 UI 和 BFF 合同，不直接运行第三方库，不写外部存储。

`/api/v1/factor-validation/external-payloads/compare` 是后续真实 payload 对比使用的 BFF 代理接口：请求体采用 `ExternalPayloadComparisonRequest`，由 `quant_ops_api` 转发到 `quant_factor_validation /api/v1/factors/external-payloads/compare`。该接口不保存 payload，不直接运行第三方库，不绕过 `quant_factor_validation` 的评分与审核规则。

`/api/v1/artifacts/ledger` 当前返回：

```text
tasks[]
artifacts[]
task_count
artifact_count
source
persistence_status
limitations
```

该接口优先读取 PostgreSQL `task_runs` / `task_artifacts` 只读账本；未配置数据库时，会退回到当前因子验证 manifest preview，用于 Web UI 先展示任务/产物结构。

配置真实账本读取：

```text
ARTIFACT_LEDGER_DATABASE_URL=postgresql+asyncpg://readonly_user:***@postgres:5432/quant_factor_validation
ARTIFACT_LEDGER_DATABASE_SCHEMA=zeta_quant_factor_validation
ARTIFACT_LEDGER_QUERY_LIMIT=20
```

如果没有单独配置 `ARTIFACT_LEDGER_DATABASE_URL`，也可以临时复用 `VALIDATION_DATABASE_URL`；如果没有单独配置 `ARTIFACT_LEDGER_DATABASE_SCHEMA`，也会回退读取 `VALIDATION_DATABASE_SCHEMA`。生产环境建议使用只读数据库用户。

配置只读对象存储读取：

```text
ARTIFACT_OBJECT_STORE_ENDPOINT=http://minio:9000
ARTIFACT_OBJECT_STORE_ACCESS_KEY=readonly_user
ARTIFACT_OBJECT_STORE_SECRET_KEY=***
ARTIFACT_OBJECT_STORE_SECURE=false
```

如果没有单独配置 `ARTIFACT_OBJECT_STORE_*`，可以复用 `VALIDATION_OBJECT_STORE_*`。该配置只用于读取 `task_artifacts` 指向的标准 JSON 产物；BFF 不写 MinIO，也不保存 access key。

101 节点已验证 `quant_ops_api` reader 可从 `zeta_quant_factor_validation` schema 读到 `validation_smoke_101_codex` 的 1 个 task 和 6 个 artifact。

101 节点已只读确认 `validation_smoke_101_codex_comparison_report`：

```text
PostgreSQL schema: zeta_quant_factor_validation
object_key: factor_validation/smoke_momentum_1d/validation_smoke_101_codex/comparison_report.json
schema_version: factor_comparison_report.v1
object_size: 2.7 KiB
factor_name: smoke_momentum_1d
primary_engine: internal
engine_count: 1
```

本地 `quant_ops_api` 已通过临时 SSH tunnel 只读联调 101 artifact：

```text
artifact_read_status: artifact_loaded
source: object_store_factor_comparison_report
artifact_id: validation_smoke_101_codex_comparison_report
factor_name: smoke_momentum_1d
```

后续本地复现使用统一命令：

```bash
make quant-ops-101-readonly-up
```

该命令只在当前进程注入 101 只读配置，不会把 PostgreSQL / MinIO 密钥写入本地文件或 Git。

## 约束 / Rules

- 只读，不直接写 PostgreSQL、ClickHouse、MinIO。
- 不保存 token、password、access key。
- 不直接 import 业务服务内部 repository / service。
- 外部状态通过明确 HTTP API 或只读 repository 查询。
- 外部因子验证 payload 对比必须代理到 `quant_factor_validation`，不能在 BFF 或 Web UI 中重新实现评分逻辑。
- 当前不替代 Prometheus / Grafana，只作为 Web UI 的轻量 BFF。

## 运行 / Run

```bash
make quant-ops-api-up
make quant-ops-api-check
```

测试：

```bash
make test-quant-ops-api
```

只读验证 `factor_comparison_report.v1` 是否已从 artifact 加载：

```bash
make smoke-quant-ops-api-comparison-artifact
```

默认期望 `artifact_read_status=artifact_loaded`。如果只是验证本地 preview fallback 链路，可以临时设置：

```bash
QUANT_OPS_EXPECTED_ARTIFACT_READ_STATUS=preview_fallback make smoke-quant-ops-api-comparison-artifact
```
