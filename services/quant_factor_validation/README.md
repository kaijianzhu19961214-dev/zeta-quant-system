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

这些字段用于后续无缝接入 MinIO / S3 兼容对象存储和 PostgreSQL `task_artifacts` 账本。当前已接入可插拔 `ValidationPersistenceService` 编排边界，但默认关闭真实持久化。

配置开关：

```text
VALIDATION_PERSISTENCE_ENABLED=false
VALIDATION_OBJECT_STORE_ENDPOINT=
VALIDATION_OBJECT_STORE_ACCESS_KEY=
VALIDATION_OBJECT_STORE_SECRET_KEY=
VALIDATION_OBJECT_STORE_BUCKET=quant-factor-data
VALIDATION_OBJECT_STORE_SECURE=false
```

当前已提供 MinIO / S3 兼容对象存储 adapter。默认值必须保持 `false`；只有在对象存储配置和 PostgreSQL 账本 repository 都配置完成后，才能切换为 `true`。否则服务会返回明确的持久化配置错误，避免误标记为 `persisted`。

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
- 自动决策只能作为候选审核状态，不能替代研究员对样本、股票池、成本和稳定性的人工复核。
- 当前在线接口默认只做只读验证计算，会返回 manifest preview 和可持久化产物元数据，但不保存报告、不写生产表、不上传 MinIO。
- 后续生产持久化必须放在 repository / integration adapter 层，不能在路由或因子统计函数中直接连接 PostgreSQL、ClickHouse 或 MinIO。
- 开启 `VALIDATION_PERSISTENCE_ENABLED=true` 前，必须同时提供对象存储配置和 PostgreSQL 账本 repository。
- 对象存储 SDK 调用必须通过 integration adapter 执行，并使用异步包装避免阻塞 FastAPI 请求处理。
