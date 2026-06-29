# 因子验证产物持久化策略

> 目标：把 `quant_factor_validation` 当前生成的验证报告、指标、IC 序列和分组收益，平滑接入生产存储。本文只约束边界和选型，不记录任何 101 节点密钥。

---

## 1. 当前已具备

`quant_factor_validation` 当前接口仍保持只读计算，不直接写 PostgreSQL、ClickHouse 或 MinIO。

但每次验证完成后，服务已经在内存中生成以下确定性 JSON payload：

```text
validation_report.json
metrics.json
ic_series.json
group_returns.json
```

返回的 `manifest.artifacts[]` 已包含：

```text
object_key
file_size_bytes
metadata.content_type = application/json
metadata.sha256
metadata.schema_version
metadata.row_count
```

这意味着后续接入对象存储时，不需要改因子验证指标计算逻辑；只需要增加 repository / integration adapter。

当前代码已接入 `ValidationPersistenceService` 编排边界和 MinIO / S3 兼容对象存储 adapter：

```text
VALIDATION_PERSISTENCE_ENABLED=false
VALIDATION_DATABASE_URL=postgresql+asyncpg://quant_admin:quant_local_password@postgres:5432/quant_factor_validation
VALIDATION_DATABASE_ECHO=false
VALIDATION_OBJECT_STORE_ENDPOINT=
VALIDATION_OBJECT_STORE_ACCESS_KEY=
VALIDATION_OBJECT_STORE_SECRET_KEY=
VALIDATION_OBJECT_STORE_BUCKET=quant-factor-data
VALIDATION_OBJECT_STORE_SECURE=false
```

默认关闭真实持久化。开启前必须同时提供对象存储配置、PostgreSQL 账本表结构和数据库连接配置；如果只打开开关但缺少任一 adapter，服务会拒绝把 manifest 标记为 `persisted`。

当前 PostgreSQL repository 已按本项目 `quant_contracts` 落地：`task_id` / `artifact_id` 使用可读业务字符串，因此 schema 使用 `varchar(128)`。字段名、索引和幂等 upsert 语义继续对齐 101 节点的 `task_runs` / `task_artifacts` 经验，但不沿用旧表里的 UUID 类型约束。

---

## 2. 生产存储分工

推荐继续沿用 101 节点已经验证过的三类存储分工：

| 存储 | 定位 | 保存内容 |
| ---- | ---- | ---- |
| PostgreSQL | 控制面和审计账本 | `task_runs`、`task_artifacts`、审核状态、运行参数、错误信息 |
| MinIO / S3 兼容对象存储 | 文件和研究产物 | JSON、Parquet、HTML/PDF 报告、图片、样本文件 |
| ClickHouse | 分析查询层 | 大规模行情、因子宽表、实验指标明细和统计聚合 |

当前这一阶段优先落 PostgreSQL + MinIO，不急于把所有验证明细写入 ClickHouse。等研究员确认指标口径后，再决定是否把 IC 序列、分组收益等写入 ClickHouse 方便批量横向比较。

---

## 3. 推荐开源依赖

Python 后端优先使用成熟、维护活跃、生态通用的开源方案：

| 能力 | 推荐方案 | 使用边界 |
| ---- | ---- | ---- |
| FastAPI 生命周期资源 | FastAPI lifespan | 初始化和关闭数据库连接池、对象存储客户端 |
| PostgreSQL async | SQLAlchemy 2.0 async + asyncpg | task/artifact 账本读写，路由层不直接写 SQL |
| MinIO 对象存储 | MinIO Python SDK 或 boto3 S3 client | 上传、下载、stat、presigned URL |
| Web UI | React + TypeScript + Vite | 只读 dashboard，不持有数据库或 MinIO 管理密钥 |

对象存储 SDK 选择建议：

- 如果生产主要使用 MinIO，优先评估 MinIO 官方 Python SDK。
- 如果未来要兼容 AWS S3、云厂商 S3 或多对象存储，优先评估 boto3 S3 client。
- 不把 SDK 调用散落在 service 业务逻辑里，统一封装为 `ArtifactObjectStore` adapter。

---

## 4. 后续实现边界

建议新增以下接口层，不改变现有因子验证计算函数：

```text
quant_factor_validation.repositories.task_run_repository
quant_factor_validation.repositories.task_artifact_repository
quant_factor_validation.integrations.artifact_object_store
quant_factor_validation.services.validation_persistence
```

建议调用顺序：

```text
FactorValidationService.validate
  -> 生成 metrics / report / ic_series / group_returns
  -> 生成 ValidationArtifactPayload
  -> enrich manifest
  -> ValidationPersistenceService.persist
      -> 上传 payload 到 MinIO / S3
      -> 写入 PostgreSQL task_runs
      -> 写入 PostgreSQL task_artifacts
      -> 返回 persisted manifest
```

MVP 默认仍应支持 `not_persisted` 模式，便于本地开发和测试环境不依赖外部存储。

当前已落地：

```text
ValidationArtifactStore 协议
ValidationLedgerRepository 协议
ValidationPersistenceService 编排
StoredValidationArtifact 回填模型
MinIO / S3 compatible object store adapter
SQLAlchemy 2.0 async PostgreSQL ledger repository
FastAPI lifespan database engine disposal
本地 PostgreSQL init schema
上传结果 size / sha256 / content_type 校验
task_runs / task_artifacts 幂等 upsert
```

后续仍待落地：

```text
生产环境迁移流程或 Alembic 版本化迁移
持久化开启后的端到端 MinIO + PostgreSQL 集成验证
只读账本查询 API
生产环境鉴权与审计日志
```

---

## 5. 强约束

- 路由层不能直接访问 PostgreSQL、ClickHouse 或 MinIO。
- 因子统计函数不能依赖外部状态，必须保持同输入同输出。
- MinIO / S3 access key、secret key、数据库密码只能来自环境变量或密钥管理系统，不能写入代码、测试快照或文档。
- 上传对象后必须校验对象大小和 checksum；不一致时不能登记为 `persisted`。
- PostgreSQL 账本登记必须幂等，同一 `task_id + artifact_id` 重试不能产生重复产物。
- 当前 schema 必须以 `quant_contracts` 为准：`task_id` 和 `artifact_id` 是业务字符串，不在 validation 服务内临时转换为 UUID。
- Web UI 只能通过后端只读 API 展示产物，不直接持有对象存储管理密钥。
- `candidate_pass` 只能表示候选通过，不等同于生产准入。

---

## 6. 参考资料

- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [SQLAlchemy asyncio extension](https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html)
- [MinIO Python SDK](https://docs.min.io/aistor/developers/sdk/python/)
- [Boto3 S3 upload_file](https://docs.aws.amazon.com/boto3/latest/reference/services/s3/client/upload_file.html)
