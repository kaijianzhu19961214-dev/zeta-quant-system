# 四层存储与记忆架构实现进度对照

更新时间：2026-06-23

本文用于对照 Obsidian 笔记 `量化研究四层存储与记忆架构.md` 中的目标架构，说明当前 `quant-data-ingestion-layer` 已经实现到什么程度、哪些能力仍处于验证或待实现阶段。

当前结论：

- 101 节点已经可以作为开发验证节点使用，已具备 ClickHouse 行情查询、MinIO 小样本数据湖、PostgreSQL 任务与产物账本、FastAPI API、Python SDK 和 Swagger。
- 生产级完整方案还没有完成，主要缺口在大规模历史数据导入、生产存储阵列、鉴权、因子专用注册表、实验指标表、数据版本表和大文件 SDK 流式传输。
- 当前最适合推进的是 `10 - 100` 只股票的完整研究链路验证，不适合在 101 当前剩余空间上导入 3T 全量数据。

## 1. 总体状态

| 层级 | 目标定位 | 当前状态 | 说明 |
|---|---|---|---|
| 第 1 层：结构化数据与对象存储 | 保存行情、因子矩阵、回测产物和原始文件 | 部分落地 | ClickHouse 行情查询和 MinIO 小样本数据湖已落地；全量数据湖和生产存储未落地 |
| 第 2 层：实验元数据与任务账本 | 记录 run_id、task_id、参数、指标、artifact、数据版本 | 部分落地 | 通用 `task_runs`、`task_artifacts` 已落地；因子实验专用表仍待设计 |
| 第 3 层：研究记忆与知识库 | 保存研究结论、方法论、会议讨论、架构决策 | 已具备基础能力 | Obsidian MCP 可读取笔记；需要持续维护 MOC、进度文档和研究总结 |
| 第 4 层：因子验证与可复现实验 | 因子计算、回测、指标评估、报告生成 | 待接入 | 当前 repo 提供数据与任务基础设施；具体因子研究代码在研究侧项目中推进 |

## 2. 第 1 层：结构化数据与对象存储

### 已落地

| 能力 | 实现位置 | 当前用途 |
|---|---|---|
| ClickHouse 行情查询 API | `app/api/v1/market.py` | 查询 `1m`、`5m`、`1d` 行情 |
| ClickHouse 查询服务 | `app/services/market_query_service.py` | 支持 `raw`、`qfq`、`hfq` 三种价格口径 |
| qfq 批次查询 | `app/api/v1/adjustments.py` | 查询前复权缓存批次 |
| MinIO 预签名上传/下载 | `app/api/v1/artifacts.py` | 研究员不直接持有 MinIO 管理密钥 |
| MinIO SDK 封装 | `quant_data_sdk/client.py` | `client.artifacts.upload_file/download_file/list_objects` |
| 101 小样本上传验证 | `docs/research_pilot_with_minio.md` | 已验证共享盘样本可以上传到 MinIO |
| 当前 MinIO bucket | 101 `.env` | `quant-factor-data` |

### 已验证样本

当前已上传到 101 MinIO 的样本对象：

```text
pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet
pilot/shared_data/sample_5m_from_1m/csv/20260105_5m_from_1m.csv
```

这些样本用于验证 MinIO 数据湖 API、SDK 上传、SDK 下载和任务产物登记流程，不代表已经复制 3T 全量共享盘。

### 未完成

| 缺口 | 影响 | 建议优先级 |
|---|---|---|
| 3T 历史数据正式导入流程 | 无法完成全市场历史查询 | 高 |
| 7T HDD 阵列接入和 IO 验证 | 生产容量与吞吐未验证 | 高 |
| 大文件 SDK 流式上传/下载 | 当前 SDK 对大文件有内存风险 | 高 |
| 数据版本 manifest | 研究结果难以稳定追溯到数据快照 | 中 |
| 全量 MinIO 数据湖目录规范 | 后续扩容时容易目录混乱 | 中 |

## 3. 第 2 层：实验元数据与任务账本

### 已落地

| 能力 | 实现位置 | 当前用途 |
|---|---|---|
| 任务表 `task_runs` | `app/models/task.py` | 记录因子计算、回测、研究导出、样本准备任务 |
| 产物表 `task_artifacts` | `app/models/task.py` | 记录 MinIO object、bucket、etag、文件大小和元数据 |
| Alembic 迁移 | `alembic/versions/0011_task_runs_and_artifacts.py` | 101 当前已迁移到 `0011_task_runs` |
| 任务 API | `app/api/v1/tasks.py` | 创建任务、查询任务、更新任务状态、登记产物 |
| 任务 SDK | `quant_data_sdk/client.py` | `client.tasks.*` 和带 `task_id` 的 artifact 上传 |
| 任务模型文档 | `docs/task_model.md` | 给研究员解释任务状态、产物类型和推荐流程 |

### 当前任务模型口径

当前开放任务类型：

```text
factor_compute
backtest
research_export
data_sample
```

当前开放产物类型：

```text
input_data
factor_result
backtest_nav
backtest_trades
backtest_report
research_export
data_sample
other
```

### 未完成

| 缺口 | 影响 | 建议优先级 |
|---|---|---|
| 因子定义表 `factor_definitions` | 无法统一管理因子名称、表达式、频率和 owner | 中 |
| 因子实验表 `factor_experiments` | 无法直接按 factor_id/run_id 聚合实验 | 中 |
| 因子指标表 `factor_metrics` | IC、RankIC、回撤、换手等指标还只能放在 `output_summary` | 中 |
| 数据版本表 `data_versions` | 不能强约束某次回测使用了哪个行情快照 | 中 |
| API 鉴权与审计 | 生产环境不应裸露任务和预签名 URL 接口 | 高 |

当前建议：短期继续使用 `task_runs` 和 `task_artifacts` 跑通研究链路；等研究员的因子命名、指标口径和回测输出稳定后，再增加因子专用表。

## 4. 第 3 层：研究记忆与知识库

### 已具备

| 能力 | 当前状态 |
|---|---|
| Obsidian MCP 检索 | 已可读取 vault 笔记 |
| 架构笔记 | 已读取 `量化研究四层存储与记忆架构.md` |
| Skills 记录 | `Codex Skills 优先级与日常使用参考.md` 已记录本机技能来源 |
| 项目 docs | 当前 repo 已维护 SDK、数据库、复权、存储、任务模型等文档 |

### 建议继续维护

| 文档 | 用途 |
|---|---|
| `docs/four_layer_implementation_progress.md` | 当前实现进度总览 |
| `docs/sdk_api_design.md` | 发给研究员的 SDK/API 使用说明 |
| `docs/task_model.md` | 研究任务和 artifact 血缘口径 |
| `docs/database_schema.md` | 数据库表结构与索引说明 |
| `docs/storage_systems.md` | PostgreSQL、ClickHouse、MinIO、文件系统各自作用 |
| `docs/research_pilot_with_minio.md` | 101 小样本研究流程验证方案 |

## 5. 第 4 层：因子验证与可复现实验

当前 `quant-data-ingestion-layer` 的定位是数据接入层和研究基础设施，不直接承载完整因子研究框架。

已经能支持研究员做的事情：

```text
通过 SDK 查询 ClickHouse 行情
通过 SDK 创建研究任务
本地或研究项目中计算因子/回测
通过 SDK 上传 parquet、json、html、图片等产物到 MinIO
通过 SDK 将产物登记到 PostgreSQL
通过 task_id 追溯一次研究任务的输入参数和输出文件
```

仍待研究侧项目补齐：

```text
因子计算框架
回测框架
指标计算
报告生成
因子注册和版本化
任务模板和标准提示词
```

## 6. 当前可交付给研究员的入口

### Swagger

```text
http://192.168.2.101:8000/docs
```

### SDK 文档

```text
docs/sdk_api_design.md
```

### 任务模型文档

```text
docs/task_model.md
```

### 研究员推荐提示词

可以让研究员 Codex 使用以下口径：

```text
你是量化研究员助手。请优先通过 quant_data_sdk 调用 101 节点的数据服务：

1. 使用 QuantDataClient.from_env() 连接内网行情 API。
2. 行情数据从 client.market.get_bars 查询，优先使用 ClickHouse 中的 1m、5m、1d 数据。
3. 原始文件、样本 parquet、回测结果和报告通过 client.artifacts 上传到 MinIO。
4. 每次因子计算或回测前，先用 client.tasks.create 创建任务。
5. 任务开始后调用 client.tasks.mark_running。
6. 产物上传时传入 task_id 和 artifact_type，确保自动登记到 task_artifacts。
7. 成功后用 client.tasks.mark_succeeded 写入指标摘要；失败时用 client.tasks.mark_failed 写入错误原因。
8. 不要把 token、密码、MinIO secret 写入代码、notebook、提示词或文档。
```

## 7. 下一阶段建议

| 优先级 | 工作项 | 说明 |
|---|---|---|
| P0 | 增加 API token 鉴权 | 生产前必须补齐，至少保护 artifacts 和 tasks 接口 |
| P1 | 验证 SDK 大文件流式上传/下载 | 代码已改为流式，仍需用 1GB、5GB parquet 做真实 MinIO 压测 |
| P1 | 接入 7T HDD 阵列并做 IO 验证 | 确认 ClickHouse、MinIO、PostgreSQL 数据目录和吞吐 |
| P1 | 增加数据版本 manifest | 让每次回测能追溯数据快照 |
| P1 | 设计因子专用表 | 等研究员确定指标口径后落地 |
| P2 | 补充 API 集成测试 | 覆盖任务、MinIO、SDK happy path 和错误路径 |

代码 review 发现与处理计划见：

```text
docs/code_review_findings.md
```

## 8. 101 开发验证边界

101 节点当前适合：

```text
小样本数据湖验证
API/SDK 联调
DBeaver 查询体验验证
10 - 100 只股票研究流程验证
任务与 artifact 血缘验证
```

101 节点当前不适合：

```text
导入 3T 全量历史数据
长期保存全量 MinIO 数据湖
生产级高并发查询
多批次前复权缓存长期并存
无鉴权对外开放 API
```
