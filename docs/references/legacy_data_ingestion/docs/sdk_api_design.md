# 内网行情 API 与 Python SDK 使用说明

## 1. 当前可用范围

本文档描述 101 开发验证节点上已经落地的 API 和 SDK 用法。

Swagger：

```text
http://192.168.2.101:8000/docs
```

当前已落地：

```text
GET  /health
GET  /api/v1/market/bars
POST /api/v1/market/bars/query
GET  /api/v1/adjustments/qfq-batches
GET  /api/v1/artifacts/objects
GET  /api/v1/artifacts/objects/stat
POST /api/v1/artifacts/presign-upload
POST /api/v1/artifacts/presign-download
POST /api/v1/tasks
GET  /api/v1/tasks
GET  /api/v1/tasks/{task_id}
PATCH /api/v1/tasks/{task_id}/status
POST /api/v1/tasks/{task_id}/artifacts
GET  /api/v1/tasks/{task_id}/artifacts
POST /api/v1/market-data/1m/batch
POST /api/v1/market-data/5m/batch
```

研究员日常优先使用：

```text
POST /api/v1/market/bars/query
GET  /api/v1/adjustments/qfq-batches
GET  /api/v1/artifacts/objects
POST /api/v1/artifacts/presign-download
POST /api/v1/artifacts/presign-upload
POST /api/v1/tasks
PATCH /api/v1/tasks/{task_id}/status
POST /api/v1/tasks/{task_id}/artifacts
```

说明：

- `market/bars` 系列接口从 ClickHouse 读取行情数据。
- 支持 `1m`、`5m`、`1d`。
- 支持 `raw` 原始价、`qfq` 前复权缓存、`hfq` 后复权视图。
- 不传 `dataset_code` 时，服务端会按频率自动使用 `a_share_1m`、`a_share_5m`、`a_share_1d`。
- `price_mode=qfq` 时必须传 `batch_id`。
- `artifacts` 系列接口通过 FastAPI 生成 MinIO 预签名 URL，研究员不需要持有 MinIO 管理密钥。
- `tasks` 系列接口记录研究任务和 MinIO 文件血缘，研究员只通过 SDK 创建、更新和查询。
- 当前 MinIO bucket 由服务端 `.env` 配置，101 验证节点为 `quant-factor-data`。
- 当前 101 开发验证阶段暂未启用 API token 鉴权；生产环境启用后 SDK 会自动从环境变量读取 token。

## 2. 环境变量

研究员本地或 Codex 运行环境建议配置：

```bash
export QUANT_DATA_API_BASE_URL="http://192.168.2.101:8000"

# 101 开发验证阶段可先不配置。
# 生产启用鉴权后再配置，SDK 会自动加入 Authorization: Bearer。
export QUANT_DATA_API_TOKEN="replace_with_researcher_token"
```

不要把 token、密码、MinIO secret 写入提示词、notebook 或代码仓库。

## 3. SDK 安装

在项目目录安装：

```bash
python -m pip install -e .
```

验证 SDK 可导入：

```bash
python - <<'PY'
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()
print(client.health())
PY
```

## 4. SDK 查询示例

### 4.1 查询前复权批次

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

batches = client.adjustments.list_qfq_batches(limit=10)
print(batches)
```

返回示例：

```json
{
  "row_count": 1,
  "batches": [
    {
      "batch_id": "qfq_20260313",
      "qfq_base_date": "2026-03-13",
      "status": "succeeded",
      "description": "generated qfq cache",
      "created_at": "2026-06-17 10:00:00",
      "finished_at": "2026-06-17 10:02:00"
    }
  ]
}
```

### 4.2 查询 1min 原始行情

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

result = client.market.get_bars(
    codes=["000001.SZ", "000651.SZ"],
    timeframe="1m",
    start="2026-03-13 09:30:00",
    end="2026-03-13 15:00:00",
    price_mode="raw",
    fields=["code", "trade_time", "open", "high", "low", "close", "vol", "amount"],
    limit=10000,
)

print(result["meta"])
print(result["rows"][:5])
```

### 4.3 查询 1min 前复权行情

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

result = client.market.get_bars(
    codes=["000001.SZ", "000651.SZ"],
    timeframe="1m",
    start="2026-03-13 09:30:00",
    end="2026-03-13 15:00:00",
    price_mode="qfq",
    batch_id="qfq_20260313",
    fields=[
        "code",
        "trade_time",
        "qfq_open",
        "qfq_high",
        "qfq_low",
        "qfq_close",
        "qfq_factor",
        "vol",
        "amount",
    ],
    limit=10000,
)

print(result["meta"])
print(result["rows"][:5])
```

### 4.4 查询 1d 后复权行情

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

result = client.market.get_bars(
    codes=["000001.SZ"],
    timeframe="1d",
    start="2026-01-05",
    end="2026-03-13",
    price_mode="hfq",
    fields=["code", "date", "hfq_open", "hfq_high", "hfq_low", "hfq_close", "hfq_factor", "vol", "amount"],
    limit=10000,
)

print(result["rows"][:5])
```

### 4.5 保存为 Parquet

```python
import pandas as pd

from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

result = client.market.get_bars(
    codes=["000001.SZ", "000651.SZ"],
    timeframe="1m",
    start="2026-03-13 09:30:00",
    end="2026-03-13 15:00:00",
    price_mode="qfq",
    batch_id="qfq_20260313",
    limit=100000,
)

df = pd.DataFrame(result["rows"])
df.to_parquet("qfq_1m_20260313.parquet", index=False)
print(len(df), df.head())
```

### 4.6 查看 MinIO 数据湖对象

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

objects = client.artifacts.list_objects(
    prefix="pilot/shared_data/",
    limit=20,
)

print(objects)
```

### 4.7 上传本地文件到 MinIO 数据湖

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

uploaded = client.artifacts.upload_file(
    local_path="qfq_1m_20260313.parquet",
    object_key="research_outputs/example/qfq_1m_20260313.parquet",
)

print(uploaded)
```

说明：

- SDK 会先向 FastAPI 请求预签名上传 URL。
- 文件通过预签名 URL 写入 MinIO。
- 研究员侧不需要知道 MinIO access key 或 secret key。

### 4.8 从 MinIO 数据湖下载文件

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

downloaded = client.artifacts.download_file(
    object_key="pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet",
    local_path="downloads/20260105_5m_from_1m.parquet",
)

print(downloaded)
```

### 4.9 创建回测任务并登记产物

```python
from quant_data_sdk import QuantDataClient

client = QuantDataClient.from_env()

task = client.tasks.create(
    task_type="backtest",
    task_name="momentum_v1_20260313",
    owner="researcher_a",
    input_params={
        "codes": ["600527.SH"],
        "timeframe": "1m",
        "price_mode": "qfq",
        "batch_id": "qfq_20260313",
    },
)

client.tasks.mark_running(task["task_id"])

artifact = client.artifacts.upload_file(
    task_id=task["task_id"],
    artifact_type="backtest_nav",
    local_path="nav.parquet",
    object_key=f"backtests/momentum_v1/{task['task_id']}/nav.parquet",
    metadata={"strategy_name": "momentum_v1"},
)

client.tasks.mark_succeeded(
    task["task_id"],
    output_summary={
        "artifact_count": 1,
        "nav_object_key": artifact["object_key"],
    },
)
```

说明：

- `client.tasks.create()` 会在 PostgreSQL `task_runs` 中创建任务。
- `client.artifacts.upload_file(task_id=...)` 会先上传 MinIO，再自动登记 `task_artifacts`。
- 研究员不需要直接写 PostgreSQL，也不需要持有 MinIO 管理密钥。

## 5. API 详情

### 5.1 健康检查

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "service": "quant-data-ingestion-layer"
}
```

### 5.2 批量查询行情

```http
POST /api/v1/market/bars/query
```

请求：

```json
{
  "timeframe": "1m",
  "codes": ["000001.SZ", "000651.SZ"],
  "start": "2026-03-13 09:30:00",
  "end": "2026-03-13 15:00:00",
  "price_mode": "qfq",
  "dataset_code": null,
  "batch_id": "qfq_20260313",
  "fields": ["code", "trade_time", "qfq_close", "qfq_factor", "vol"],
  "limit": 10000
}
```

参数说明：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---:|---|
| timeframe | string | 是 | `1m`、`5m`、`1d` |
| codes | string[] | 是 | 证券代码列表 |
| start | string | 是 | 开始日期或时间 |
| end | string | 是 | 结束日期或时间 |
| price_mode | string | 否 | `raw`、`qfq`、`hfq`，默认 `raw` |
| dataset_code | string | 否 | 留空时按频率使用 `a_share_1m`、`a_share_5m`、`a_share_1d` |
| batch_id | string | 条件必填 | `price_mode=qfq` 时必填 |
| fields | string[] | 否 | 返回字段，留空使用默认字段 |
| limit | int | 否 | `1 - 100000`，默认 `10000` |

返回：

```json
{
  "meta": {
    "timeframe": "1m",
    "price_mode": "qfq",
    "dataset_code": "a_share_1m",
    "batch_id": "qfq_20260313",
    "row_count": 2,
    "limit": 10000
  },
  "rows": [
    {
      "code": "000001.SZ",
      "trade_time": "2026-03-13 09:30:00",
      "qfq_close": "10.120000",
      "qfq_factor": "1.0000000000",
      "vol": 123456
    }
  ]
}
```

### 5.3 GET 查询行情

```http
GET /api/v1/market/bars
```

适合短股票列表和 Swagger 页面手动测试。

示例：

```text
http://192.168.2.101:8000/api/v1/market/bars?timeframe=1m&codes=000001.SZ,000651.SZ&start=2026-03-13%2009:30:00&end=2026-03-13%2015:00:00&price_mode=qfq&batch_id=qfq_20260313&fields=code,trade_time,qfq_close,vol&limit=1000
```

### 5.4 查询前复权批次

```http
GET /api/v1/adjustments/qfq-batches?limit=100
```

用途：

- 查看当前可用 `batch_id`。
- 给 `price_mode=qfq` 查询使用。

返回：

```json
{
  "row_count": 1,
  "batches": [
    {
      "batch_id": "qfq_20260313",
      "qfq_base_date": "2026-03-13",
      "status": "succeeded",
      "description": "generated qfq cache",
      "created_at": "2026-06-17 10:00:00",
      "finished_at": "2026-06-17 10:02:00"
    }
  ]
}
```

### 5.5 列出 MinIO 数据湖对象

```http
GET /api/v1/artifacts/objects?prefix=pilot/shared_data/&limit=100
```

用途：

- 查看 MinIO 中已经入湖的原始文件、parquet 子集、研究产物。
- 研究员可用它确认文件是否存在。

返回：

```json
{
  "bucket_name": "quant-factor-data",
  "prefix": "pilot/shared_data/",
  "row_count": 1,
  "objects": [
    {
      "bucket_name": "quant-factor-data",
      "object_key": "pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet",
      "size": 6248891,
      "etag": "replace_with_etag",
      "last_modified": "2026-06-18T17:40:00+00:00",
      "content_type": null
    }
  ]
}
```

### 5.6 查询 MinIO 对象元信息

```http
GET /api/v1/artifacts/objects/stat?object_key=pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet
```

返回对象大小、etag、content_type、last_modified。

### 5.7 生成预签名上传地址

```http
POST /api/v1/artifacts/presign-upload
```

请求：

```json
{
  "object_key": "research_outputs/example/result.parquet",
  "content_type": "application/octet-stream",
  "expires_seconds": 3600
}
```

返回：

```json
{
  "bucket_name": "quant-factor-data",
  "object_key": "research_outputs/example/result.parquet",
  "method": "PUT",
  "url": "http://192.168.2.101:9000/...",
  "expires_in": 3600
}
```

### 5.8 生成预签名下载地址

```http
POST /api/v1/artifacts/presign-download
```

请求：

```json
{
  "object_key": "pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet",
  "expires_seconds": 3600
}
```

返回：

```json
{
  "bucket_name": "quant-factor-data",
  "object_key": "pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet",
  "method": "GET",
  "url": "http://192.168.2.101:9000/...",
  "expires_in": 3600
}
```

### 5.9 创建研究任务

```http
POST /api/v1/tasks
```

请求：

```json
{
  "task_type": "backtest",
  "task_name": "momentum_v1_20260313",
  "owner": "researcher_a",
  "description": "动量策略小样本回测",
  "input_params": {
    "codes": ["600527.SH"],
    "timeframe": "1m",
    "price_mode": "qfq",
    "batch_id": "qfq_20260313"
  }
}
```

返回：

```json
{
  "task_id": "replace_with_task_id",
  "task_type": "backtest",
  "task_name": "momentum_v1_20260313",
  "owner": "researcher_a",
  "status": "created",
  "description": "动量策略小样本回测",
  "input_params": {
    "codes": ["600527.SH"]
  },
  "output_summary": null,
  "error_message": null,
  "created_at": "2026-06-18T18:30:00+08:00",
  "updated_at": "2026-06-18T18:30:00+08:00",
  "started_at": null,
  "finished_at": null
}
```

### 5.10 更新任务状态

```http
PATCH /api/v1/tasks/{task_id}/status
```

请求：

```json
{
  "status": "succeeded",
  "output_summary": {
    "annual_return": 0.12,
    "max_drawdown": -0.08,
    "artifact_count": 2
  },
  "error_message": null
}
```

状态枚举：

```text
created
running
succeeded
failed
cancelled
```

### 5.11 登记任务产物

```http
POST /api/v1/tasks/{task_id}/artifacts
```

请求：

```json
{
  "artifact_type": "backtest_nav",
  "artifact_name": "nav.parquet",
  "object_key": "backtests/momentum_v1/replace_with_task_id/nav.parquet",
  "metadata": {
    "strategy_name": "momentum_v1"
  }
}
```

说明：

- `object_key` 必须已经上传到 MinIO。
- 服务端会读取 MinIO 元信息，写入 `bucket_name`、`uri`、`file_size_bytes` 和 `etag`。
- `task_artifacts` 不使用数据库外键，只通过 `task_id` 索引关联任务。

### 5.12 查询任务和产物

```http
GET /api/v1/tasks?task_type=backtest&status=succeeded&limit=20
GET /api/v1/tasks/{task_id}
GET /api/v1/tasks/{task_id}/artifacts
```

### 5.13 数据写入接口

```http
POST /api/v1/market-data/1m/batch
POST /api/v1/market-data/5m/batch
```

这两个接口主要给数据接入服务使用，不建议研究员日常手动调用。

## 6. 字段说明

常用 raw 字段：

```text
code
trade_time
date
open
high
low
close
pre_close
change
pct_chg
vol
amount
vwap
adj_factor
hfq_factor
source_name
```

常用 qfq 字段：

```text
code
trade_time
date
qfq_open
qfq_high
qfq_low
qfq_close
qfq_pre_close
qfq_change
qfq_vwap
qfq_factor
vol
amount
```

常用 hfq 字段：

```text
code
trade_time
date
hfq_open
hfq_high
hfq_low
hfq_close
hfq_pre_close
hfq_change
hfq_vwap
hfq_factor
vol
amount
```

注意：

- `trade_time` 只适用于 `1m` 和 `5m`。
- `vwap`、`qfq_vwap`、`hfq_vwap` 当前只适用于 `1d`。

## 7. 给研究员的 Codex 提示词

```text
请使用 quant_data_sdk 查询 101 节点行情数据。
从环境变量读取 QUANT_DATA_API_BASE_URL 和 QUANT_DATA_API_TOKEN。
不要在输出中展示任何 token、密码或 MinIO 密钥。

先调用 client.adjustments.list_qfq_batches(limit=10) 获取可用 batch_id。
然后查询 000001.SZ 和 000651.SZ 在 2026-03-13 的 1min 前复权数据，
price_mode 使用 qfq，batch_id 使用可用批次。
字段包括 code、trade_time、qfq_close、qfq_factor、vol、amount。
将结果保存为 parquet，并输出行数、时间范围和前 5 行摘要。
```

MinIO 数据湖文件访问提示词：

```text
请使用 quant_data_sdk 访问 101 节点 MinIO 数据湖。
从环境变量读取 QUANT_DATA_API_BASE_URL 和 QUANT_DATA_API_TOKEN。
不要在输出中展示任何 token、密码或 MinIO 密钥。

先调用 client.artifacts.list_objects(prefix="pilot/shared_data/", limit=20)
查看可验证样本文件。
然后下载 pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet
到本地 downloads 目录，读取 parquet 的行数、列名和前 5 行摘要。
```

研究任务与产物登记提示词：

```text
请使用 quant_data_sdk 创建一次 backtest 研究任务。
从环境变量读取 QUANT_DATA_API_BASE_URL 和 QUANT_DATA_API_TOKEN。
不要在输出中展示任何 token、密码或 MinIO 密钥。

任务名称为 momentum_v1_20260313，owner 使用 researcher_a。
任务 input_params 记录 codes、timeframe、price_mode、batch_id。
任务创建后标记为 running。
读取 ClickHouse 前复权行情，完成一个最小回测示例。
将 nav.parquet 和 summary.json 上传到 MinIO，并通过 task_id 自动登记为 task_artifacts。
最后将任务标记为 succeeded，并在 output_summary 中写入行数、产物数量和核心指标。
```

## 8. 当前未纳入本版 SDK 的能力

以下能力仍在后续阶段：

```text
研究产物审批、保留周期和权限策略
多研究员角色权限和审计
任务取消后的自动清理策略
```

当前 `client.tasks`、`client.artifacts` 已可用；研究员仍不需要直接操作 PostgreSQL 或 MinIO 管理密钥。
