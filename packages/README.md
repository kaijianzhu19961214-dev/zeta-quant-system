# Packages / 公共包

`packages/` 保存多个服务共享的 Python 包。公共包必须保持轻量、稳定、低耦合，优先放协议、类型、纯函数和跨服务复用的工具。

`packages/` stores shared Python packages used by multiple services. These packages should stay lightweight, stable, and loosely coupled.

## 当前包 / Current Packages

```text
quant_contracts/  # shared schemas, enums, errors, naming rules, pure utilities
```

## 约束 / Rules

- 公共包不能直接连接 PostgreSQL、ClickHouse、MinIO 或第三方数据源。
- 公共包不能读取真实 `.env` 或持有密钥。
- 公共包优先使用 Pydantic v2 模型表达输入输出。
- 公共包中的纯函数使用 `def`，I/O 不应出现在公共协议层。
- 公共包变更需要评估对 `services/` 和 `clients/` 的兼容影响。

