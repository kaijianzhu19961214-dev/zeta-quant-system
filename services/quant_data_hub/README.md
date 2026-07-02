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

容器启动：

```bash
make quant-data-hub-build
make quant-data-hub-up
make quant-data-hub-check
```

默认端口：

```text
http://127.0.0.1:18000
```

101 只读 smoke test：

```bash
make smoke-quant-data-hub-101
```

前提：

- 本地 `.env` 已配置 101 ClickHouse 连接。
- Mac 已打开 `127.0.0.1:18123 -> 101:18123` SSH tunnel。
- `quant_data_hub` 容器已重启并读取本地 `.env`。

## 行情查询 API 示例 / Market Query Examples

标准接口：

```text
POST /api/v1/market-bars/query
```

raw 原始价格：

```json
{
  "timeframe": "1d",
  "symbols": ["000001.SZ"],
  "start": "2026-03-13",
  "end": "2026-03-13",
  "price_mode": "raw",
  "fields": ["symbol", "trade_date", "close_price", "volume", "adjustment_factor"]
}
```

响应关键字段：

```json
{
  "meta": {
    "timeframe": "1d",
    "price_mode": "raw",
    "dataset_code": "a_share_1d",
    "batch_id": null,
    "qfq_base_date": null
  },
  "rows": [
    {
      "symbol": "000001.SZ",
      "trade_date": "2026-03-13",
      "close_price": "10.20",
      "volume": "1000",
      "adjustment_factor": "1.0000000000"
    }
  ]
}
```

qfq 前复权价格：

```json
{
  "timeframe": "1d",
  "symbols": ["000001.SZ"],
  "start": "2026-03-13",
  "end": "2026-03-13",
  "price_mode": "qfq",
  "batch_id": "qfq_20260313",
  "fields": ["symbol", "trade_date", "close_price", "volume", "adjustment_factor"]
}
```

响应关键字段：

```json
{
  "meta": {
    "price_mode": "qfq",
    "batch_id": "qfq_20260313",
    "qfq_base_date": "2026-03-13"
  },
  "rows": [
    {
      "close_price": "10.20",
      "volume": "1000",
      "adjustment_factor": "1.0000000000"
    }
  ]
}
```

hfq 后复权价格：

```json
{
  "timeframe": "1d",
  "symbols": ["000001.SZ"],
  "start": "2026-03-13",
  "end": "2026-03-13",
  "price_mode": "hfq",
  "fields": ["symbol", "trade_date", "close_price", "volume", "adjustment_factor"]
}
```

响应关键字段：

```json
{
  "meta": {
    "price_mode": "hfq",
    "batch_id": null,
    "qfq_base_date": null
  },
  "rows": [
    {
      "close_price": "10.20",
      "volume": "1000",
      "adjustment_factor": "1.0000000000"
    }
  ]
}
```

约束：

- `price_mode=qfq` 必须提供 `batch_id`。
- `qfq_base_date` 由服务根据 `batch_id` 从 `qfq_batches` 解析并返回。
- `adjustment_factor` 表示当前 `price_mode` 下生效的复权因子。
- 同一次因子计算只能使用一种明确价格口径。

Tushare 真实小样本 smoke test：

```bash
make smoke-tushare-factor-sample
```

用途：

- 使用本机环境变量 `TUSHARE_TOKEN` 通过 Tushare SDK 读取一小段真实 A 股日线和 `adj_factor`。
- 如果使用兼容 Tushare HTTP 协议的代理 Key，需要同时设置 `TUSHARE_PROXY_BASE_URL`，例如 `https://tt.xiaodefa.cn` 或访问更快的同类域名。
- 将 Tushare 字段转换为 `quant_contracts.MarketBar`，再复用 `quant_factor_lab` 的 momentum 纯函数和 `quant_factor_validation` 的 IC / Rank IC 指标函数。
- 默认不落盘、不写 PostgreSQL / ClickHouse / MinIO、不打印明细行情和 token。

本地配置示例：

```bash
export TUSHARE_TOKEN="<your_local_token>"
export TUSHARE_PROXY_BASE_URL="https://tt.xiaodefa.cn"  # 使用代理 Key 时配置；官方 Tushare token 可不配
export TUSHARE_SMOKE_SYMBOLS="000001.SZ,000651.SZ,000333.SZ,600000.SH,600519.SH"
export TUSHARE_SMOKE_START_DATE="20260601"
export TUSHARE_SMOKE_END_DATE="20260610"
export TUSHARE_SMOKE_PRICE_MODE="qfq"
```

说明：

- `TUSHARE_TOKEN` 只能放在本机 shell、`.env` 或部署平台密钥管理中，不能提交到 Git。
- 官方 Tushare token 默认走 `tushare.pro_api(token)`；代理 Key 必须走 `TUSHARE_PROXY_BASE_URL`，否则官方 SDK 会返回 token 不正确。
- qfq 模式必须同时读取 `adj_factor`；缺少复权因子时 smoke 会失败，避免用 raw price 冒充前复权数据。
- 该 smoke 只是本地集成验证入口，生产级 Tushare 入库仍应落在 `quant_data_hub` ingestion adapter，而不是让 `quant_factor_lab` 直接依赖 Tushare SDK。

## 约束 / Rules

- 默认通过 API 或只读小样本验证，不从 101 全量复制数据到 Mac。
- 导入任务必须记录数据源、时间范围、版本、批次和产物位置。
- API 输入输出必须复用 `quant_contracts`。
- 连接 101 的 smoke test 必须手动触发，并且默认只读或 dry-run。
- Tushare token、订单号、购买权限信息属于本地私有配置，不能写入 README、代码、测试 fixture 或 Git 历史。
