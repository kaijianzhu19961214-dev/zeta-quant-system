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
GET /api/v1/factor-validation/review
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

101 节点已验证 `quant_ops_api` reader 可从 `zeta_quant_factor_validation` schema 读到 `validation_smoke_101_codex` 的 1 个 task 和 6 个 artifact。

## 约束 / Rules

- 只读，不直接写 PostgreSQL、ClickHouse、MinIO。
- 不保存 token、password、access key。
- 不直接 import 业务服务内部 repository / service。
- 外部状态通过明确 HTTP API 或只读 repository 查询。
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
