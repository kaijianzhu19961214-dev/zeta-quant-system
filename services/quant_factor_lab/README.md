# quant_factor_lab / 因子计算服务

`quant_factor_lab` 负责因子定义、因子计算和因子产物生成。第一版只依赖 `quant_data_hub` 的标准行情接口，允许受控兼容第三方原始数据读取。

`quant_factor_lab` calculates factors and produces factor artifacts. The MVP should use `quant_data_hub` as the default data source while allowing controlled third-party raw-data adapters.

## 职责 / Responsibilities

- 定义因子输入、参数、窗口、频率和输出 schema。
- 调用 `quant_data_hub` 或 `quant_data_sdk` 获取标准行情数据。
- 生成因子值、因子元数据和计算产物 manifest。
- 将因子产物交给 MinIO 或后续统一 artifact 存储。

## 当前 MVP / Current MVP

当前已落地最小 FastAPI 服务：

```text
GET  /health
POST /api/v1/factors/calculate
```

第一批只实现：

```text
momentum_*d = close_price / close_price.shift(N) - 1
```

示例：

```bash
curl -sS http://127.0.0.1:18010/health
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/factors/calculate \
  -H 'content-type: application/json' \
  -d '{
    "factor_name": "momentum_20d",
    "symbols": ["000001.SZ"],
    "start": "2026-01-01",
    "end": "2026-03-13",
    "lookback_window": 20
  }'
```

运行测试：

```bash
make test-quant-factor-lab
```

启动容器：

```bash
make quant-factor-lab-up
make quant-factor-lab-check
```

## 第三方原始数据兼容 / Third-Party Raw Data Compatibility

允许兼容读取第三方原始数据，但必须满足：

- 只能通过明确的 adapter 接入，不能在因子代码中散落第三方 API 调用。
- adapter 输出必须转换为 `quant_contracts` 的标准模型。
- 读取过程必须记录 source、version、time_range、field_mapping 和 license 约束。
- 生产默认路径仍应优先走 `quant_data_hub`，避免因子服务变成第二套数据接入系统。

## 不做什么 / Non-Goals

- 不负责长期保存原始行情数据。
- 不绕过数据协议直接写入 ClickHouse。
- 不承担因子有效性统计和报告生成；这部分属于 `quant_factor_validation`。
