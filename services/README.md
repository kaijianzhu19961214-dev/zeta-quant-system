# Services / 服务

`services/` 保存可独立部署、测试和维护的业务服务。第一版只落地 MVP 相关服务，后续服务通过新增目录迭代，不大改第一版边界。

`services/` stores independently deployable business services. The MVP starts with the core services and keeps boundaries stable for later iterations.

## MVP 服务 / MVP Services

```text
quant_data_hub/              # data ingestion, storage, query, lineage
quant_factor_lab/            # factor calculation
quant_factor_validation/     # factor validation and reports
quant_ops_api/               # read-only operations aggregation API
```

## 后续服务 / Later Services

```text
quant_model_lab/
quant_backtest_engine/
quant_risk_engine/
quant_execution_gateway/
```

## 服务约束 / Service Rules

- 服务之间优先通过 API、SDK 或 `quant_contracts` 协议交互。
- 每个服务独立拥有 README、配置样例、测试和迁移说明。
- FastAPI 服务使用 Pydantic v2、SQLAlchemy 2.0、异步 I/O 和生命周期上下文管理器。
- 路由层只做参数校验和响应编排，业务逻辑下沉到 service/repository 层。
- 真实数据、大文件、密钥和生产 `.env` 不进入仓库。
