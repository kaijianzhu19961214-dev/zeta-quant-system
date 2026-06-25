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
- 通过 `quant_ops_api /api/v1/artifacts/ledger` 展示任务账本和产物账本预览。
- 提供加载、刷新和错误态，保持只读边界。

当前 Factor Validation 页仍是 `not_persisted` 预览，不表示报告已经入库或上传 MinIO。

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
