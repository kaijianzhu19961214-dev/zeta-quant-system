# 101 旧数据接入项目重合分析与迁移清单

> 来源：`192.168.2.101:/home/ddd/ZeTa-quant-data-ingestion-layer`。本文件只记录结构和经验，不包含真实密钥和大规模行情数据。

---

## 1. 结论

101 上的 `ZeTa-quant-data-ingestion-layer` 与当前方案中的 `quant_data_hub` 高度重合，可以作为 `quant_data_hub` 的前身实现参考。

当前建议：

```text
Mac:
  代码管理、文档、测试、小样本 fixture、Codex 开发

101:
  PostgreSQL 控制面
  ClickHouse 行情分析主存储
  MinIO 原始文件 / 研究产物存储
  大规模行情数据与导入任务
```

不建议把 101 的 PostgreSQL、ClickHouse、MinIO 大数据复制到 Mac。

---

## 2. 远程项目现状

远程项目路径：

```text
/home/ddd/ZeTa-quant-data-ingestion-layer
```

运行服务：

```text
FastAPI:    http://192.168.2.101:8000
PostgreSQL: localhost:5432 on 101
ClickHouse: http://127.0.0.1:18123 on 101
MinIO:      192.168.2.101:9000
```

已验证 API：

```text
GET  /health
POST /api/v1/market/bars/query
GET  /api/v1/adjustments/qfq-batches
```

当前 API 样例返回正常：

```text
/health -> {"status": "ok", "service": "quant-data-ingestion-layer"}
```

---

## 3. 数据资产摘要

### 3.1 PostgreSQL

定位：控制面、小规模验证表、任务与产物血缘。

数据库：

```text
quant_data_ingestion
```

核心表：

```text
datasets
securities
trading_calendar
ingestion_jobs
market_data_1d
market_data_1m
market_data_5m
adjustment_factors
qfq_batches
task_runs
task_artifacts
```

当前行数：

```text
market_data_1d: 10,345
market_data_1m: 1,249,103
market_data_5m: 253,967
task_runs: 1
task_artifacts: 1
```

注意：

- `datasets`、`securities`、`trading_calendar` 当前行数为 0，说明主数据链路还需要补齐。
- PostgreSQL 不应作为分钟线长期分析主存储。

### 3.2 ClickHouse

定位：行情分析主存储与高速查询层。

数据库：

```text
quant_market
```

核心表：

```text
market_data_1d_raw
market_data_1m_raw
market_data_5m_raw
adjustment_factors
qfq_batches
market_data_1d_qfq_cache
market_data_1m_qfq_cache
market_data_5m_qfq_cache
v_market_data_1d_hfq
v_market_data_1m_hfq
v_market_data_5m_hfq
```

当前数据覆盖：

```text
market_data_1d_raw:
  rows: 54,438
  codes: 5,528
  range: 2026-01-05 ~ 2026-06-10

market_data_1m_raw:
  rows: 1,249,103
  codes: 5,183
  range: 2026-03-13 09:30:00 ~ 2026-03-13 15:00:00

market_data_5m_raw:
  rows: 253,967
  codes: 5,183
  range: 2026-03-13 09:30:00 ~ 2026-03-13 15:00:00
```

qfq 批次：

```text
qfq_20260313
qfq_20260610
```

### 3.3 MinIO

定位：原始文件、研究样本、因子结果、回测产物、报告等对象存储。

bucket：

```text
quant-factor-data
```

已有对象类型：

```text
custom/dashboard_latest-*/latest.json
custom/manifest-*/manifest.json
factor-metrics/momentum_20d/*/metrics.json
pilot/shared_data/sample_5m_from_1m/*
research_tasks/*/data_sample/*.parquet
```

---

## 4. 与当前 MVP 的重合点

### 4.1 quant_data_hub

高度重合，可以优先吸收：

```text
数据接入脚本
PostgreSQL 控制面模型
ClickHouse raw/qfq/hfq 表设计
行情查询 API
复权逻辑
任务与产物血缘
MinIO 预签名 URL 服务
节点巡检脚本
```

### 4.2 quant_contracts

部分重合，可以抽象为公共协议：

```text
行情 bar schema
行情查询 request/response schema
qfq batch schema
task run schema
task artifact schema
```

### 4.3 quant_factor_lab

弱重合。

旧项目里有 MinIO 的 `factor-metrics/momentum_20d` 产物路径，但尚未形成正式的：

```text
factor_daily_value
factor_calculation_service
统一因子计算接口
```

### 4.4 quant_factor_validation

弱重合。

旧项目目前未形成正式的：

```text
IC
Rank IC
ICIR
分组收益
多空收益
factor_validation_report
```

---

## 5. 字段口径差异

旧项目字段偏数据源原始口径：

```text
code
date
open
high
low
close
vol
amount
```

当前新方案文档中曾倾向业务语义字段：

```text
symbol
trade_date
open_price
high_price
low_price
close_price
volume
turnover
```

建议：

- `quant_contracts` 对外 schema 使用业务语义字段。
- `quant_data_hub` 内部存储允许保留旧项目字段，以便兼容 ClickHouse 和供应商原始字段。
- 在 repository/service 层提供字段映射，不要求大表重命名。

---

## 6. 优先迁移候选

第一批只迁移代码，不迁移数据：

```text
ClickHouse 查询 service
qfq / hfq 复权逻辑
Tushare 日线导入脚本
inspect_node_inventory 巡检脚本
task_runs / task_artifacts 血缘模型
quant_data_sdk
```

暂不迁移：

```text
.env
.venv
真实数据文件
PostgreSQL 数据目录
ClickHouse 数据目录
MinIO 数据目录
日志和缓存
```

---

## 7. 推荐迁移顺序

1. 保留 101 作为数据基础设施节点。
2. 当前仓库先吸收文档、DDL、migration 作为参考。
3. 在 `packages/quant_contracts` 中定义兼容 schema。
4. 将旧项目代码迁入 `services/quant_data_hub`。
5. 把 `quant_data_sdk` 抽到 `clients/quant_data_sdk`。
6. 本地 Mac 通过远程 API 或 SSH tunnel 做只读开发验证。
7. `quant_factor_lab` 和 `quant_factor_validation` 后续直接消费 101 的 ClickHouse/API。

---

## 8. 当前参考材料位置

```text
docs/references/legacy_data_ingestion/
```

关键文件：

```text
docs/references/legacy_data_ingestion/docs/data_flow_architecture.md
docs/references/legacy_data_ingestion/docs/database_schema.md
docs/references/legacy_data_ingestion/docs/price_adjustment_logic.md
docs/references/legacy_data_ingestion/docs/sdk_api_design.md
docs/references/legacy_data_ingestion/docs/task_model.md
docs/references/legacy_data_ingestion/deploy/clickhouse/initdb/001_market_data.sql
docs/references/legacy_data_ingestion/alembic/versions/
```

