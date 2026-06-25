# quant_data_hub / 数据中心服务

`quant_data_hub` 是系统的数据接入、存储、查询和血缘服务。它是 101 旧数据接入项目的主要迁移目标。

`quant_data_hub` is the data ingestion, storage, query, and lineage service. It is the main migration target for the legacy 101 data-ingestion project.

## 职责 / Responsibilities

- 接入 Tushare、共享盘、交易所文件或其他第三方原始数据。
- 管理 PostgreSQL 控制面数据：任务、元数据、血缘、小型校验表。
- 管理 ClickHouse 行情分析库：raw、qfq、hfq、分钟线和日线查询。
- 管理 MinIO 对象存储索引：原始文件、中间产物、研究产物。
- 提供标准行情查询 API 和内部 SDK 数据源能力。

## 生产存储 / Production Storage

```text
PostgreSQL:
  control plane, metadata, task runs, artifacts, lineage

ClickHouse:
  market data analytical store, raw/qfq/hfq bars

MinIO:
  raw files, intermediate artifacts, factor outputs, reports
```

Mac 本地不保存全量真实数据；生产数据继续保留在 101 节点。

## 迁移优先级 / Migration Priority

优先迁移：

- ClickHouse 查询 service。
- qfq / hfq 复权逻辑。
- Tushare 导入脚本。
- `inspect_node_inventory` 巡检脚本。
- task / artifact 血缘模型。

迁移前先对照：

- [101 旧数据接入项目重合分析与迁移清单](../../docs/legacy_data_ingestion_overlap_and_migration.md)
- [旧项目参考材料](../../docs/references/legacy_data_ingestion/README_IMPORT.md)

## 当前进度 / Current Progress

已落地第一批服务代码：

- `GET /health`
- `POST /api/v1/market-bars/query`
- `POST /api/v1/market/bars/query` 旧接口兼容入口
- `GET /api/v1/market/bars` 旧接口兼容入口
- `GET /api/v1/adjustments/qfq-batches`
- ClickHouse SQL builder
- 异步 ClickHouse HTTP client
- 不连接真实 101 的 unittest

测试：

```bash
make test-quant-data-hub
```

## 约束 / Rules

- 默认通过 API 或只读小样本验证，不从 101 全量复制数据到 Mac。
- 导入任务必须记录数据源、时间范围、版本、批次和产物位置。
- API 输入输出必须复用 `quant_contracts`。
- 连接 101 的 smoke test 必须手动触发，并且默认只读或 dry-run。
