# quant_data_sdk / 数据客户端 SDK

`quant_data_sdk` 是 `quant_data_hub` 的 Python 客户端，用于研究脚本、因子服务和验证服务调用标准行情数据。

`quant_data_sdk` is the Python client for `quant_data_hub`.

## 当前状态 / Current Status

当前 SDK 已提供同步与异步客户端。研究脚本可使用同步客户端，FastAPI 等服务内调用优先使用异步客户端。

The SDK provides both synchronous and asynchronous clients. Research scripts can use the sync client; FastAPI-style services should prefer the async client.

## 职责 / Responsibilities

- 封装行情查询和复权批次查询。
- 将 API 响应转换为 `quant_contracts` 模型。
- 支持小样本验证和只读远程查询。
- 为 notebook / script / service 调用提供一致接口。
- 后续扩展任务状态查询和产物索引查询。

## 不做什么 / Non-Goals

- 不直接连接生产数据库。
- 不内置真实 101 节点密钥。
- 不默认落盘全量行情数据。
- 不替代 `quant_data_hub` 的服务端校验和血缘记录。

## 后续迁移 / Later Migration

从 101 旧项目迁移 SDK 时，应优先保留稳定 API 形态，再逐步替换字段模型为 `quant_contracts`。

## 安装 / Install

仓库内开发安装：

Editable install inside this repository:

```bash
python -m pip install -e packages/quant_contracts -e clients/quant_data_sdk
```

## 使用示例 / Usage

通过环境变量配置服务地址：

Configure the service URL with an environment variable:

```bash
export QUANT_DATA_HUB_BASE_URL=http://127.0.0.1:18000
```

查询健康状态和日线行情：

Query service health and daily bars:

```python
from quant_contracts import Timeframe
from quant_data_sdk import QuantDataClient

with QuantDataClient.from_env() as client:
    health = client.health()
    bars = client.market.get_bars(
        symbols=["000001.SZ"],
        timeframe=Timeframe.DAY_1,
        start="2026-03-13",
        end="2026-03-13",
        fields=["symbol", "trade_date", "close_price"],
    )

print(health.status)
print(bars.meta.row_count)
```

查询前复权批次：

List qfq batches:

```python
from quant_data_sdk import QuantDataClient

with QuantDataClient.from_env() as client:
    batches = client.adjustments.list_qfq_batches(limit=10)

print([batch.batch_id for batch in batches.batches])
```

异步服务内调用：

Async service call:

```python
from quant_contracts import Timeframe
from quant_data_sdk import AsyncQuantDataClient

async with AsyncQuantDataClient.from_env() as client:
    bars = await client.market.get_bars(
        symbols=["000001.SZ"],
        timeframe=Timeframe.DAY_1,
        start="2026-03-13",
        end="2026-03-13",
    )
```

## 测试 / Tests

```bash
make test-quant-data-sdk
```

单元测试使用 `httpx.MockTransport`，不会访问真实 101 节点或本地服务。

Unit tests use `httpx.MockTransport`; they do not call the real 101 node or local service.
