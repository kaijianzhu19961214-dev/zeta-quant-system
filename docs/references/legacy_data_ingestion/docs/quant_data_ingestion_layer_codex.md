# quant-data-ingestion-layer

## 1. 项目定位

`quant-data-ingestion-layer` 是一个面向私募基金量化投研场景的量化数据接入层服务。

该服务不负责因子计算、回测、策略执行或交易下单，只负责将第三方获取到的量化相关数据通过 Web API 接入系统，完成基础校验、标准化处理和 PostgreSQL 落库，为公司内部开发人员、研究员和后续因子计算服务提供统一、稳定、可查询的数据存储入口。

## 2. 中文名称

量化数据接入层

## 3. 英文项目名

`quant-data-ingestion-layer`

## 4. 核心业务流程

```text
第三方数据源
    ↓
数据转手获取 / 拉取 / 推送
    ↓
FastAPI Web 接入服务
    ↓
字段校验、格式标准化、去重、批量写入
    ↓
PostgreSQL 结构化存储
    ↓
公司内部开发读取数据
    ↓
因子计算、研究分析、回测系统
```

## 5. 当前服务边界

### 负责

- 接收第三方量化数据
- 提供 HTTP API 写入接口
- 使用 Pydantic v2 进行请求参数校验
- 对数据做轻量预处理
  - 字段标准化
  - 时间格式转换
  - 空值校验
  - 重复数据处理
  - 数据来源标记
  - 根据 `qfq_factor`、`hfq_factor` 生成前复权和后复权价格
- 不在行情大表上使用外键，避免影响批量导入和查询性能
- 使用批量写入方式落库 PostgreSQL
- 提供基础查询接口，方便内部开发验证数据
- 提供健康检查接口
- 提供基础日志、错误处理和性能监控入口

### 不负责

- 不做因子计算
- 不做回测
- 不做策略执行
- 不做交易下单
- 不承担复杂数据分析任务
- 不在本服务内运行重计算任务

## 6. 推荐技术栈

```text
Python 3.11+
FastAPI
Pydantic v2
PostgreSQL
SQLAlchemy 2.0 async / asyncpg
Alembic
Uvicorn
Nginx，可选
Docker / systemd
unittest
```

## 7. 推荐架构分层

```text
app/
  main.py
  api/
    routes/
      health.py
      market_data.py
      datasets.py
  core/
    config.py
    logging.py
    database.py
    exceptions.py
  schemas/
    market_data.py
    dataset.py
    ingestion_job.py
    common.py
  models/
    base.py
    market_data.py
    dataset.py
    ingestion_job.py
  repositories/
    market_data_repository.py
    dataset_repository.py
    ingestion_job_repository.py
  services/
    market_data_service.py
    dataset_service.py
  utils/
    time_utils.py
    batch_utils.py
tests/
  test_health.py
  test_market_data_api.py
  test_market_data_service.py
alembic/
pyproject.toml
README.md
.env.example
```

## 8. 主要模块说明

### API 层

负责 HTTP 请求入口，包含：

- 请求参数校验
- 调用 service 层
- 返回统一响应
- 处理 HTTPException
- 不在路由中直接写复杂业务逻辑

### Service 层

负责业务编排，包含：

- 数据预处理
- 数据去重
- 批量写入控制
- 业务错误转换
- 调用 repository 层

### Repository 层

负责数据库访问，包含：

- 批量插入
- 查询
- upsert
- 事务控制
- 数据库异常封装

### Schema 层

负责请求和响应模型，使用 Pydantic v2。

### Model 层

负责 SQLAlchemy ORM 模型定义。

## 9. 数据库设计原则

### 基础原则

- PostgreSQL 作为核心存储
- 大表按时间分区
- 高频写入表减少索引数量
- 优先使用批量写入
- 避免单条数据频繁 insert
- 控制数据库连接数
- 内部服务通过连接池访问 PostgreSQL

### 推荐索引

优先保留：

```sql
(dataset_code, code, trade_time)
```

或根据业务使用：

```sql
(dataset_code, trade_time)
(dataset_code, date, code)
```

避免对每个字段都创建索引。

行情表维护策略：

- 历史数据按批次导入，正式表唯一键防止重复写入。
- 日表唯一键为 `(dataset_code, code, date)`。
- 1min/5min 唯一键为 `(dataset_code, code, trade_time)`。
- 生产历史数据优先使用 `COPY -> staging 表 -> 校验/去重 -> 正式分区表`。
- API 批量写入用于开发验证、小批量补导和接口联调。

## 10. 初始数据表设计方向

### 数据集表

用于记录数据来源和数据类型。

```text
datasets
- id
- dataset_code
- dataset_name
- source_name
- description
- is_active
- created_at
- updated_at
```

### 市场数据表

用于存储标准化后的行情或预处理数据。

```text
market_data
- id
- dataset_code
- symbol
- trade_time
- trade_date
- open_price
- high_price
- low_price
- close_price
- volume
- amount
- source_name
- raw_payload
- created_at
```

### 写入日志表

用于记录批量写入情况。

```text
ingestion_jobs
- id
- job_id
- dataset_code
- source_name
- received_count
- inserted_count
- skipped_count
- failed_count
- status
- error_message
- started_at
- finished_at
```

## 11. 核心接口设计

### 健康检查

```http
GET /health
```

返回服务状态。

### 批量写入市场数据

```http
POST /api/v1/market-data/batch
```

用于接收一批市场数据并批量写入 PostgreSQL。

### 查询写入任务

```http
GET /api/v1/ingestion-jobs/{job_id}
```

用于查询某次写入任务的结果。

### 查询数据集

```http
GET /api/v1/datasets
```

用于查看当前支持的数据集。

## 12. 批量写入策略

推荐 API 一次接收多条数据，例如：

```json
{
  "dataset_code": "daily_price",
  "source_name": "third_party_vendor",
  "rows": [
    {
      "symbol": "000001.SZ",
      "trade_time": "2026-06-11T09:30:00+08:00",
      "open_price": 10.12,
      "high_price": 10.30,
      "low_price": 10.01,
      "close_price": 10.20,
      "volume": 100000,
      "amount": 1020000
    }
  ]
}
```

返回：

```json
{
  "job_id": "uuid",
  "received_count": 1,
  "inserted_count": 1,
  "skipped_count": 0,
  "failed_count": 0
}
```

## 13. 性能原则

- FastAPI worker 数量初期建议 1 到 2 个
- PostgreSQL 连接池初期建议 5 到 10 个连接
- API 不建议单条写入
- 每批建议 500 到 5000 条数据
- 大批量历史数据导入优先使用 COPY
- 高频写入表不要建立过多索引
- PostgreSQL 数据目录优先放 SSD / NVMe
- 避免在当前机器上同时运行回测和复杂因子计算

## 14. 部署建议

当前已确认的业务边界：

- 暂不处理秒级数据
- 当前最高数据频率为每分钟级别
- 不做实时数据接入
- 第三方购买的数据先落到本地共享盘
- 本服务负责将共享盘数据批量同步到 PostgreSQL
- PostgreSQL 为内部人员和 Codex 查询、计算提供统一数据源
- 历史分钟级数据预计约 3T

详细开发方案和生产方案见：

```text
docs/development_and_production_plan.md
```

当前机器资源：

```text
CPU: Intel i5-8400，6 核 6 线程
Memory: 7.6 GiB
Swap: 4 GiB
```

适合部署：

```text
开发验证环境
FastAPI Web 服务
PostgreSQL
Nginx，可选
日志采集，可选
```

开发验证阶段只使用 101 单节点：

```text
101:
  FastAPI
  PostgreSQL
  DBeaver / Codex 通过 SSH Tunnel 或远端连接访问
```

生产阶段保留主从方案：

```text
101:
  PostgreSQL Primary
  FastAPI 导入任务服务
  负责共享盘文件批量导入

102:
  PostgreSQL Replica
  负责内部人员、Codex、DBeaver 只读查询
```

不建议在同一台机器上同时运行：

```text
大规模回测
复杂因子计算
全市场高频 Level2 计算
大型分析查询
```

## 14.1 开发验证阶段方案

开发阶段先实现单节点方案，目标是尽快完成数据模型、导入流程和查询验证。

```text
共享盘样本数据
    ↓
101 FastAPI / 导入脚本
    ↓
字段校验、时间标准化、去重
    ↓
PostgreSQL staging 表
    ↓
COPY / 批量写入
    ↓
PostgreSQL 分区正式表
    ↓
内部读取验证
```

开发阶段要求：

- 只实现分钟级数据
- 优先实现共享盘文件批量导入
- 暂不实现实时写入
- 暂不实现秒级数据
- 暂不强制部署主从
- 代码层面预留 `WRITE_DATABASE_URL` 和 `READ_DATABASE_URL`
- 开发阶段两个数据库连接可以指向同一个 101 PostgreSQL
- 使用 `unittest` 验证核心逻辑

## 14.2 生产阶段方案

生产阶段采用 PostgreSQL 主从结构，用于隔离导入和查询压力。

```text
第三方数据文件
    ↓
本地共享盘
    ↓
101 PostgreSQL Primary
    ↓ PostgreSQL Streaming Replication
102 PostgreSQL Replica
    ↓
内部人员 / Codex / DBeaver / 查询接口
```

生产职责划分：

- 101 Primary
  - 数据导入
  - 数据校验
  - 分区管理
  - Alembic migration
  - ingestion job 记录
  - 主数据写入
- 102 Replica
  - 只读查询
  - 内部人员读取
  - Codex 读取
  - DBeaver 查询
  - 查询 API

生产配置预留：

```env
WRITE_DATABASE_URL=postgresql+asyncpg://quant_writer:***@101:5432/quant_data_ingestion
READ_DATABASE_URL=postgresql+asyncpg://quant_reader:***@102:5432/quant_data_ingestion
```

生产存储建议：

```text
101 主库:
  SSD / NVMe:
    OS
    FastAPI
    PostgreSQL 配置
    PostgreSQL WAL，推荐

  HDD RAID5:
    PostgreSQL data_directory
    3T 历史分钟级行情数据

102 从库:
  优先 SSD / NVMe 数据盘
  查询性能优先时，RAID10 优于 RAID5
```

生产节点建议：

```text
101 主库:
  CPU: 8 核起步，推荐 12 到 16 核
  内存: 32GiB 起步，推荐 64GiB
  系统盘: SSD / NVMe 256GiB+
  WAL 盘: SSD / NVMe 200GiB+
  数据盘: 8 HDD RAID5 / RAID6 / RAID10

102 从库:
  CPU: 12 到 16 核
  内存: 64GiB 起步，推荐 128GiB
  数据盘: SSD / NVMe 优先
```

如果只能优先升级一类资源，查询节点优先增加内存。

## 15. 推荐 PostgreSQL 参数方向

```conf
shared_buffers = 2GB
effective_cache_size = 5GB
work_mem = 16MB
maintenance_work_mem = 512MB

max_connections = 30

wal_buffers = 16MB
checkpoint_timeout = 15min
max_wal_size = 4GB
min_wal_size = 1GB
```

如果使用 asyncpg 连接池：

```text
min_size = 2
max_size = 10
```

## 16. 工程质量要求

- 使用类型注解
- 使用 Pydantic v2 定义请求和响应模型
- 使用 SQLAlchemy 2.0 async 或 asyncpg
- 使用 Repository / Service / API 分层
- 使用统一错误处理
- 使用统一日志
- 使用 `.env` 管理配置
- 不在路由函数中写复杂 SQL
- 不在路由函数中直接处理复杂业务逻辑
- 优先早返回处理异常情况
- 避免深层嵌套
- 批量写入必须有单元测试
- API 参数校验必须有测试
- 数据库写入逻辑必须有测试

## 17. 第一阶段目标

第一阶段只实现最小可用版本：

- FastAPI 项目骨架
- PostgreSQL 异步连接池
- 健康检查接口
- 市场数据批量写入接口
- 数据集基础模型
- 写入任务日志模型
- Alembic 初始化
- 基础单元测试
- README 和 `.env.example`

## 18. 第二阶段目标

- 增加数据去重策略
- 增加 upsert 支持
- 增加分区表
- 增加写入性能压测脚本
- 增加慢查询和连接数监控 SQL
- 增加 Nginx 部署示例
- 增加 systemd 或 Docker Compose 部署方式

## 19. 交付目标

最终交付一个可运行、可测试、可扩展的量化数据接入层服务，为后续公司内部因子计算服务提供稳定的数据存储入口。

---

# Codex 初始化提示词

你现在需要帮我实现一个 Python FastAPI 项目，项目名为 `quant-data-ingestion-layer`。

这是一个面向私募基金量化投研场景的“量化数据接入层”服务。它不负责因子计算、回测、策略执行或交易下单，只负责接收第三方转手获取到的量化数据，通过 Web API 完成字段校验、轻量标准化、批量写入 PostgreSQL，并提供给公司内部开发人员读取，用于后续因子计算。

请按照下面要求生成项目骨架和第一阶段代码。

## 技术栈

- Python 3.11+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.0 async
- asyncpg
- PostgreSQL
- Alembic
- Uvicorn
- unittest
- python-dotenv 或 pydantic-settings

## 项目结构

请使用如下目录结构：

```text
app/
  main.py
  api/
    routes/
      health.py
      market_data.py
      datasets.py
  core/
    config.py
    database.py
    logging.py
    exceptions.py
  schemas/
    common.py
    market_data.py
    dataset.py
    ingestion_job.py
  models/
    base.py
    market_data.py
    dataset.py
    ingestion_job.py
  repositories/
    market_data_repository.py
    dataset_repository.py
    ingestion_job_repository.py
  services/
    market_data_service.py
    dataset_service.py
  utils/
    time_utils.py
tests/
  test_health.py
  test_market_data_api.py
  test_market_data_service.py
alembic/
.env.example
README.md
pyproject.toml
```

## 编码要求

- 所有函数必须有类型注解
- 同步纯函数使用 `def`
- 异步 I/O 使用 `async def`
- 使用 Pydantic v2 模型做请求和响应校验
- 使用 SQLAlchemy 2.0 async 管理 PostgreSQL
- 使用 Repository / Service / API 分层
- 路由层只负责 HTTP 入参、调用 service、返回响应
- 业务逻辑放在 service 层
- 数据库操作放在 repository 层
- 使用早返回处理错误情况，避免深层嵌套
- 使用统一响应模型
- 使用统一异常处理
- 使用日志记录关键写入任务
- 不要在路由函数中直接写 SQL
- 不要实现因子计算、回测、交易下单功能

## 第一阶段需要实现

### 1. 配置模块

实现 `app/core/config.py`：

- 使用 Pydantic Settings
- 支持从 `.env` 读取配置
- 至少包含：
  - `app_name`
  - `environment`
  - `database_url`
  - `log_level`

### 2. 数据库模块

实现 `app/core/database.py`：

- 创建 async SQLAlchemy engine
- 创建 async session factory
- 提供 `get_db_session` 依赖
- 使用 lifespan 管理资源

### 3. 健康检查接口

实现：

```http
GET /health
```

返回：

```json
{
  "status": "ok",
  "service": "quant-data-ingestion-layer"
}
```

### 4. 数据模型

实现以下 ORM 模型：

#### Dataset

字段：

- `id`
- `dataset_code`
- `dataset_name`
- `source_name`
- `description`
- `is_active`
- `created_at`
- `updated_at`

#### MarketData

字段：

- `id`
- `dataset_code`
- `symbol`
- `trade_time`
- `trade_date`
- `open_price`
- `high_price`
- `low_price`
- `close_price`
- `volume`
- `amount`
- `source_name`
- `raw_payload`
- `created_at`

#### IngestionJob

字段：

- `id`
- `job_id`
- `dataset_code`
- `source_name`
- `received_count`
- `inserted_count`
- `skipped_count`
- `failed_count`
- `status`
- `error_message`
- `started_at`
- `finished_at`

### 5. 市场数据批量写入接口

实现：

```http
POST /api/v1/market-data/batch
```

请求示例：

```json
{
  "dataset_code": "daily_price",
  "source_name": "third_party_vendor",
  "rows": [
    {
      "symbol": "000001.SZ",
      "trade_time": "2026-06-11T09:30:00+08:00",
      "open_price": 10.12,
      "high_price": 10.30,
      "low_price": 10.01,
      "close_price": 10.20,
      "volume": 100000,
      "amount": 1020000
    }
  ]
}
```

响应示例：

```json
{
  "job_id": "uuid",
  "received_count": 1,
  "inserted_count": 1,
  "skipped_count": 0,
  "failed_count": 0
}
```

### 6. 写入逻辑

- 如果 `rows` 为空，返回 400
- 自动从 `trade_time` 解析 `trade_date`
- 使用批量插入
- 创建 ingestion job 日志
- 写入成功后更新 job 状态
- 写入失败时记录错误信息
- 初始版本可以先不做复杂去重，但代码结构要预留 upsert 扩展点

### 7. 测试

使用 `unittest` 编写基础测试：

- 健康检查接口测试
- market data 请求参数校验测试
- 空 rows 返回 400 测试
- service 层 trade_date 解析测试
- repository 层可先用 mock，避免强依赖真实数据库

## 输出要求

请直接生成完整项目文件，不要只给片段。
每个文件保持职责单一。
代码需要可以被后续继续扩展。
不要实现与本项目无关的复杂功能。

---

# Codex 分阶段任务提示词

## 第 1 步：生成项目骨架

请根据 `docs/project_overview.md` 中的项目说明，为 `quant-data-ingestion-layer` 生成 FastAPI 项目骨架。先只创建目录、配置模块、数据库连接模块、健康检查接口、README、`.env.example` 和基础测试。不要实现复杂业务逻辑。

## 第 2 步：实现数据库模型和 Alembic

请为项目增加 SQLAlchemy 2.0 async ORM 模型，包括 `Dataset`、`MarketData`、`IngestionJob`。配置 Alembic，使其可以自动识别模型 metadata。生成初始化 migration。注意字段命名使用小写下划线。

## 第 3 步：实现市场数据批量写入接口

请实现 `POST /api/v1/market-data/batch`。要求使用 Pydantic v2 校验请求体，service 层解析 `trade_date`，repository 层执行批量插入，并记录 ingestion job。空 rows 返回 400。不要在路由层直接写 SQL。

## 第 4 步：补充单元测试

请使用 unittest 为健康检查、market data 参数校验、空 rows、trade_date 解析、service 层写入编排逻辑补充测试。repository 可以使用 mock，不要求依赖真实 PostgreSQL。

## 第 5 步：补充部署文档

请补充部署说明，包括 `.env` 配置、PostgreSQL 初始化、Alembic migration、Uvicorn 启动命令、systemd 示例、Nginx 反向代理示例和基础性能检查命令。

---

# 附录：基础性能验证命令

## 确认 PostgreSQL 数据目录

```bash
sudo -u postgres psql -Atc "show data_directory;"
```

## 查看数据目录所在磁盘

```bash
PGDATA=$(sudo -u postgres psql -Atc "show data_directory;")
df -hT "$PGDATA"
findmnt -T "$PGDATA"
lsblk -o NAME,TYPE,SIZE,ROTA,MODEL,MOUNTPOINT,FSTYPE
```

## 磁盘实时 I/O

```bash
iostat -x 1
```

## PostgreSQL 综合压测

```bash
sudo -u postgres createdb quant_bench
sudo -u postgres pgbench -i -s 50 quant_bench
sudo -u postgres pgbench -c 10 -j 4 -T 60 -P 5 quant_bench
```

## 查看连接数

```bash
sudo -u postgres psql -c "
SELECT
    state,
    count(*) AS connection_count
FROM pg_stat_activity
GROUP BY state
ORDER BY connection_count DESC;
"
```

## 查看活跃 SQL

```bash
sudo -u postgres psql -c "
SELECT
    pid,
    usename,
    state,
    wait_event_type,
    wait_event,
    now() - query_start AS duration,
    left(query, 120) AS query
FROM pg_stat_activity
WHERE state <> 'idle'
ORDER BY duration DESC;
"
```

## 查看表和索引大小

```bash
sudo -u postgres psql -d quant_bench -c "
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
    pg_size_pretty(pg_relation_size(relid)) AS table_size,
    pg_size_pretty(pg_indexes_size(relid)) AS indexes_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 20;
"
```
