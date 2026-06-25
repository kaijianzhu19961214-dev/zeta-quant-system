# quant_contracts / 公共协议包

`quant_contracts` 是系统的公共协议层，用于统一字段命名、数据模型、枚举、错误语义和跨服务 API 契约。

`quant_contracts` is the shared contract layer for schemas, naming, enums, errors, and API contracts.

## 职责 / Responsibilities

- 定义行情、证券、交易日历、复权、任务、产物、因子和验证结果的数据模型。
- 承接 101 旧项目 schema / API / SDK 字段，形成新的公共命名规范。
- 为 `quant_data_hub`、`quant_factor_lab`、`quant_factor_validation` 和 `quant_data_sdk` 提供稳定协议。
- 保存纯函数工具，例如 symbol / timeframe / adjustment mode 的标准化。

## 不做什么 / Non-Goals

- 不直接访问数据库。
- 不直接请求 Tushare、交易所、券商或第三方 API。
- 不包含服务路由、后台任务、调度器或存储实现。
- 不保存真实数据、token、password、access key。

## 建议结构 / Suggested Structure

```text
src/quant_contracts/
  market_data/
  securities/
  calendars/
  adjustments/
  factors/
  lineage/
  errors/
tests/
```

## 迁移入口 / Legacy Mapping

旧项目字段和新协议的映射以此文档为准：

- [quant_contracts 与 101 旧数据接入项目协议映射](../../docs/quant_contracts_legacy_mapping.md)

任何从 101 旧项目迁移进来的 schema，都应先在这里完成命名和兼容性确认，再进入具体服务。

