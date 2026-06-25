# 研究任务与产物血缘模型

## 1. 定位

`task_runs` 和 `task_artifacts` 是量化研究流程的任务账本。

它们解决的问题：

```text
谁在什么时候做了什么研究任务
这个任务用了哪些输入参数
这个任务当前是什么状态
这个任务产出了哪些 MinIO 文件
后续如何追溯、复查、清理和复用这些产物
```

研究员不需要理解 PostgreSQL 表结构，也不需要直接操作 MinIO 密钥。

研究员只通过 SDK 使用：

```python
task = client.tasks.create(...)
client.artifacts.upload_file(task_id=task["task_id"], ...)
client.tasks.mark_succeeded(task["task_id"])
```

## 2. 任务类型

第一版只开放研究员常用任务类型：

| task_type | 中文含义 | 使用场景 |
|---|---|---|
| factor_compute | 因子计算 | 计算并保存因子值、因子暴露、因子 IC 等 |
| backtest | 回测 | 运行策略回测并保存净值、交易明细、指标摘要 |
| research_export | 研究导出 | 导出研究中间结果、样本、报告 |
| data_sample | 样本准备 | 准备小样本数据集，供回测或验证使用 |

暂不让研究员直接创建数据接入类任务。

数据接入、前复权缓存、历史数据导入仍由平台侧脚本或服务处理。

## 3. 任务状态

任务状态由平台定义，研究员只按 SDK 方法表达意图。

| status | 中文含义 | 谁触发 |
|---|---|---|
| created | 已创建 | `client.tasks.create()` |
| running | 运行中 | `client.tasks.mark_running()` |
| succeeded | 成功 | `client.tasks.mark_succeeded()` |
| failed | 失败 | `client.tasks.mark_failed()` |
| cancelled | 已取消 | 平台或后续 SDK 扩展 |

时间戳规则：

- 创建任务时写入 `created_at`。
- 标记 `running` 时写入 `started_at`。
- 标记 `succeeded`、`failed`、`cancelled` 时写入 `finished_at`。
- 每次状态变化写入 `updated_at`。

## 4. 产物类型

任务产物记录在 `task_artifacts`。

| artifact_type | 中文含义 | 常见文件 |
|---|---|---|
| input_data | 输入数据 | parquet、csv |
| factor_result | 因子结果 | factor_values.parquet |
| backtest_nav | 回测净值 | nav.parquet |
| backtest_trades | 回测交易明细 | trades.parquet |
| backtest_report | 回测报告 | summary.json、report.html |
| research_export | 研究导出 | 任意研究中间结果 |
| data_sample | 数据样本 | sample.parquet |
| other | 其他 | 临时文件或补充材料 |

## 5. 研究员推荐流程

```text
1. 创建任务
2. 查询 ClickHouse 行情
3. 本地计算因子或回测
4. 上传结果文件到 MinIO
5. SDK 自动登记 task_artifacts
6. 标记任务成功或失败
```

示例：

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

client.artifacts.upload_file(
    task_id=task["task_id"],
    artifact_type="backtest_nav",
    local_path="nav.parquet",
    object_key=f"backtests/momentum_v1/{task['task_id']}/nav.parquet",
    metadata={"strategy_name": "momentum_v1"},
)

client.tasks.mark_succeeded(
    task["task_id"],
    output_summary={
        "annual_return": 0.12,
        "max_drawdown": -0.08,
        "artifact_count": 1,
    },
)
```

## 6. 平台侧约束

- 不在 `task_runs.input_params` 中写入 token、密码、MinIO secret。
- `task_artifacts` 不使用数据库外键，只用 `task_id` 建索引关联任务。
- MinIO 访问由 FastAPI 服务端生成预签名 URL。
- SDK 不直接暴露 MinIO 管理密钥。
- 研究员侧只需要知道 `task_id` 和 `object_key`。

## 7. 当前上线 API

```text
POST  /api/v1/tasks
GET   /api/v1/tasks
GET   /api/v1/tasks/{task_id}
PATCH /api/v1/tasks/{task_id}/status
POST  /api/v1/tasks/{task_id}/artifacts
GET   /api/v1/tasks/{task_id}/artifacts
```

Swagger：

```text
http://192.168.2.101:8000/docs
```
