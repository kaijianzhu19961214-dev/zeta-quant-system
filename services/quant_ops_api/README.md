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

该接口只暴露因子验证审核摘要和 manifest preview。当前 `latest_metric` 包含 IC、Rank IC、分组数和高低分组收益差均值；manifest preview 包含 report、metrics、ic_series、group_returns 四类产物，不代表报告已写入 PostgreSQL、MinIO 或生产 artifact 表。

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

该接口把当前因子验证 manifest preview 映射成只读任务/产物账本形态，用于 Web UI 先展示 `task_runs` / `task_artifacts` 结构。当前 `persistence_status = not_persisted`，不代表已经接入 101 节点 PostgreSQL 或生产 MinIO。后续正式版本应通过只读 API、只读视图或受控 manifest 对象接入真实账本。

## 约束 / Rules

- 只读，不直接写 PostgreSQL、ClickHouse、MinIO。
- 不保存 token、password、access key。
- 不直接 import 业务服务内部 repository / service。
- 外部状态只通过明确 HTTP API 查询。
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
