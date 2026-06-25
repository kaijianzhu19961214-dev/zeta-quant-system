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

当前仅建立需求和目录边界，前端代码后续按 `docs/web_ui_and_monitoring_requirements.md` 分阶段实现。

