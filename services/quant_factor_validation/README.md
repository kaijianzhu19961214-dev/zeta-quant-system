# quant_factor_validation / 因子验证服务

`quant_factor_validation` 负责对因子产物进行统计检验、分组回测式验证和报告生成。

`quant_factor_validation` validates factor artifacts and produces research reports.

## 职责 / Responsibilities

- 读取因子产物、行情收益和股票池定义。
- 计算 IC、Rank IC、分组收益、换手、覆盖率、缺失率和稳定性指标。
- 输出结构化验证结果和可复现报告。
- 记录验证任务、参数、输入产物、输出产物和代码版本。

## 输入 / Inputs

```text
factor artifact
market return data
universe definition
calendar
validation config
```

## 输出 / Outputs

```text
metrics tables
figures
markdown / html / pdf reports
artifact manifest
```

## 当前 MVP / Current MVP

当前已落地最小 FastAPI 服务：

```text
GET  /health
POST /api/v1/factors/validate
```

第一批只计算：

```text
forward_return_n
IC
Rank IC
IC mean
Rank IC mean
IC std
ICIR
group_returns
group_return_spread_mean
coverage_ratio
missing_ratio
validation report summary
artifact manifest preview
factor score card
factor comparison report
```

结构化审核摘要包含：

```text
decision: insufficient_data | review_required | candidate_pass | candidate_reject
summary
findings
recommended_actions
```

结构化 manifest 当前用于描述后续可持久化的任务和产物清单：

```text
manifest.persistence_status = not_persisted
manifest.task_run
manifest.artifacts
```

接口会在内存中生成以下确定性 JSON 产物 payload，并把产物元数据回填到 manifest：

```text
validation_report.json
metrics.json
ic_series.json
group_returns.json
score_card.json
comparison_report.json
```

每个 `manifest.artifacts[]` 当前包含：

```text
object_key
file_size_bytes
metadata.content_type = application/json
metadata.sha256
metadata.schema_version
metadata.row_count
```

评分卡当前在线 API 仍使用 `internal` 规则评分引擎，输出透明 `score_components`、`final_score` 和 `review_decision`。服务层已提供 `ExternalFactorValidationSummary -> FactorEvaluationResult` 的标准 adapter，可把 Alphalens、Qlib、vectorbt、OpenSourceAP/CrossSection 和 commodity-curve-factors 的核心统计结果映射回统一评分与比较协议；这些库当前不作为运行依赖。

这些字段用于后续无缝接入 MinIO / S3 兼容对象存储和 PostgreSQL `task_artifacts` 账本。当前已接入可插拔 `ValidationPersistenceService` 编排边界，但默认关闭真实持久化。

配置开关：

```text
VALIDATION_PERSISTENCE_ENABLED=false
VALIDATION_DATABASE_URL=postgresql+asyncpg://quant_admin:quant_local_password@postgres:5432/quant_factor_validation
VALIDATION_DATABASE_ECHO=false
VALIDATION_DATABASE_SCHEMA=
VALIDATION_OBJECT_STORE_ENDPOINT=
VALIDATION_OBJECT_STORE_ACCESS_KEY=
VALIDATION_OBJECT_STORE_SECRET_KEY=
VALIDATION_OBJECT_STORE_BUCKET=quant-factor-data
VALIDATION_OBJECT_STORE_SECURE=false
VALIDATION_SMOKE_CREATE_SCHEMA=true
VALIDATION_SMOKE_CREATE_BUCKET=false
VALIDATION_SMOKE_RUN_ID=validation_smoke_local
```

当前已提供 MinIO / S3 兼容对象存储 adapter 和 SQLAlchemy 2.0 async PostgreSQL 账本 repository。默认值必须保持 `false`；只有在对象存储、数据库表结构和生产密钥都配置完成后，才能切换为 `true`。否则服务会返回明确的持久化配置错误，避免误标记为 `persisted`。

PostgreSQL 账本使用：

```text
task_runs
task_artifacts
```

本项目当前 contracts 使用可读业务字符串作为 `task_id` / `artifact_id`，因此本地 schema 使用 `varchar(128)`，字段名和索引形态继续对齐 101 节点历史模型。

如果复用 101 旧项目数据库，必须配置独立 schema，例如 `VALIDATION_DATABASE_SCHEMA=zeta_quant_factor_validation`，避免命中旧 public schema 下 UUID 版 `task_runs` / `task_artifacts`。

持久化端到端 smoke：

```bash
make smoke-quant-factor-validation-persistence
```

该命令在 `quant_factor_validation` 容器内执行：

```text
1. 校验 MinIO / S3 bucket 是否存在
2. 可选创建 PostgreSQL task_runs / task_artifacts schema
3. 运行一组固定小样本因子验证
4. 上传 validation_report / metrics / ic_series / group_returns / score_card / comparison_report
5. 写入 task_runs / task_artifacts
6. 校验 manifest.persisted、账本行数和对象大小
```

真实执行前必须通过 `.env` 或部署平台注入 `VALIDATION_DATABASE_URL`、`VALIDATION_OBJECT_STORE_ENDPOINT`、`VALIDATION_OBJECT_STORE_ACCESS_KEY` 和 `VALIDATION_OBJECT_STORE_SECRET_KEY`。命令不会打印密钥。

101 节点验证记录：

```text
2026-06-30 validation_smoke_101_codex
schema: zeta_quant_factor_validation
manifest persisted: manifest_validation_smoke_101_codex
postgres ledger: task_count=1, artifact_count=6
object store: bucket=quant-factor-data, object_count=6
```

示例：

```bash
curl -sS http://127.0.0.1:18020/health
```

```bash
curl -sS http://127.0.0.1:18020/api/v1/factors/validate \
  -H 'content-type: application/json' \
  -d '{
    "factor_name": "momentum_1d",
    "factor_values": [
      {
        "symbol": "000001.SZ",
        "trade_date": "2026-03-13",
        "factor_name": "momentum_1d",
        "factor_value": "0.1"
      }
    ],
    "market_start": "2026-03-13",
    "market_end": "2026-03-16",
    "forward_days": 1
  }'
```

运行测试：

```bash
make test-quant-factor-validation
```

启动容器：

```bash
make quant-factor-validation-up
make quant-factor-validation-check
```

## 约束 / Rules

- 验证逻辑必须可复现：同一输入、同一配置、同一代码版本应得到一致结果。
- 指标模型和报告摘要字段必须复用 `quant_contracts`。
- 外部验证库输出必须先汇总为 `ExternalFactorValidationSummary`，再由 adapter 映射为 `FactorValidationMetric` / `FactorEvaluationResult`。
- 自动决策只能作为候选审核状态，不能替代研究员对样本、股票池、成本和稳定性的人工复核。
- 当前在线接口默认只做只读验证计算，会返回 manifest preview 和可持久化产物元数据，但不保存报告、不写生产表、不上传 MinIO。
- 后续生产持久化必须放在 repository / integration adapter 层，不能在路由或因子统计函数中直接连接 PostgreSQL、ClickHouse 或 MinIO。
- 开启 `VALIDATION_PERSISTENCE_ENABLED=true` 前，必须同时提供对象存储配置、`VALIDATION_DATABASE_URL` 和已初始化的 PostgreSQL 账本表。
- 对象存储 SDK 调用必须通过 integration adapter 执行，并使用异步包装避免阻塞 FastAPI 请求处理。
- PostgreSQL 写入必须通过 SQLAlchemy 2.0 async repository 执行，并在 FastAPI lifespan 中释放连接池。
- 持久化 smoke 只能使用环境变量读取密钥，不允许把 101 节点或生产 MinIO 密钥写入文档、测试或提交历史。
