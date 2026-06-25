# quant_data_sdk / 数据客户端 SDK

`quant_data_sdk` 是 `quant_data_hub` 的 Python 客户端，用于研究脚本、因子服务和验证服务调用标准行情数据。

`quant_data_sdk` is the Python client for `quant_data_hub`.

## 职责 / Responsibilities

- 封装行情查询、复权数据查询、任务状态查询和产物索引查询。
- 将 API 响应转换为 `quant_contracts` 模型。
- 支持小样本验证和只读远程查询。
- 为 notebook / script / service 调用提供一致接口。

## 不做什么 / Non-Goals

- 不直接连接生产数据库。
- 不内置真实 101 节点密钥。
- 不默认落盘全量行情数据。
- 不替代 `quant_data_hub` 的服务端校验和血缘记录。

## 后续迁移 / Later Migration

从 101 旧项目迁移 SDK 时，应优先保留稳定 API 形态，再逐步替换字段模型为 `quant_contracts`。

