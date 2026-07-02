# 量化多项目架构与 Codex 实施方案

> 适用场景：私募基金量化研究平台早期建设。目标是将“数据 → 因子 → 因子验证 → 模型/信号 → 回测 → 风控 → 执行”拆成多个边界清晰的小项目，便于 Codex 分阶段生成、测试和维护。

---

## 1. 核心结论

不建议把所有功能都塞进一个大项目里。对当前阶段更稳妥的方式是：

```text
多个独立项目 + 一个公共协议项目 quant_contracts
```

也就是：

```text
quant_contracts              # 公共协议层：schema、枚举、错误类型、通用工具
quant_data_hub               # 数据接入层：行情/财务/基础数据接入、清洗、入库
quant_factor_lab             # 因子计算层：量价因子、截面因子、基础预处理
quant_factor_validation      # 因子验证层：IC、Rank IC、分组收益、多空收益、覆盖率
quant_model_lab              # 模型层：因子组合、打分模型、机器学习模型
quant_backtest_engine        # 回测层：持仓、调仓、净值、手续费、滑点、绩效指标
quant_risk_engine            # 风控层：仓位约束、行业暴露、回撤控制、流动性限制
quant_execution_gateway      # 执行层：模拟交易/实盘交易接口，后期再做
quant_research_workspace     # 研究工作区：notebook、临时实验、报告草稿
quant_ops_web                # 运营监控层：服务状态、任务血缘、产物和报告展示
```

第一阶段不要追求全部完成，先跑通：

```text
标准行情数据 → 因子计算 → 因子有效性验证报告
```

这个闭环稳定后，再做回测、模型、风控和执行。

结合 101 节点已有验证环境，当前更推荐的落地方式是：

```text
Mac / GitHub 公共仓库
    负责代码、文档、测试、migration、配置样例和 Codex 开发

101 数据基础设施节点
    负责 PostgreSQL、ClickHouse、MinIO、真实行情数据和导入任务
```

也就是说，Mac 不保存大规模数据库和对象存储数据；本地只保留代码、小样本 fixture 和可复现测试。

---

## 2. 为什么不建议一开始做成一个大项目

如果使用 Codex 辅助开发，一个大项目容易出现以下问题：

1. 职责边界混乱：因子计算代码可能混到回测里，回测代码可能直接改数据接入逻辑。
2. 上下文污染：Codex 一次读到太多文件，容易把不同模块的规则混在一起。
3. 测试困难：一个模块改动后，可能影响全项目测试。
4. 协作困难：同事只想用数据接口，却被迫理解因子、回测、风控代码。
5. 后期拆分成本高：业务一旦跑起来，再拆会很痛苦。

更推荐从一开始就让每个项目“只做一件事”。

---

## 3. 总体依赖关系

核心原则：**所有业务项目都可以依赖 quant_contracts，但业务项目之间不要随意互相依赖。**

推荐数据流：

```text
quant_data_hub
    ↓ 输出标准行情数据
quant_factor_lab
    ↓ 输出因子值
quant_factor_validation
    ↓ 输出因子评价报告
quant_model_lab
    ↓ 输出交易信号
quant_backtest_engine
    ↓ 输出回测结果
quant_risk_engine
    ↓ 输出风控后目标仓位
quant_execution_gateway
    ↓ 输出模拟/实盘订单
quant_ops_web
    ↘ 旁路读取服务状态、任务血缘、artifact manifest 和报告索引
```

依赖方向建议：

```text
quant_contracts
    ↑
    ├── quant_data_hub
    ├── quant_factor_lab
    ├── quant_factor_validation
    ├── quant_model_lab
    ├── quant_backtest_engine
    ├── quant_risk_engine
    └── quant_execution_gateway
```

不建议出现：

```text
quant_factor_lab 直接调用 quant_risk_engine
quant_backtest_engine 直接修改 quant_data_hub 的原始数据
quant_model_lab 直接写入原始行情表
quant_execution_gateway 直接计算因子
quant_ops_web 直接连接生产数据库或绕过服务 API 修改生产数据
```

---

## 4. 全项目统一技术规范

建议统一以下规则，避免每个项目风格不一致。

### 4.1 Python 与依赖

```text
Python 3.12+
FastAPI
Pydantic v2
SQLAlchemy 2.0 async
asyncpg
PostgreSQL
ClickHouse
MinIO
Redis 7
Alembic
unittest
ruff
mypy，暂不全量开启
```

### 4.2 代码风格

- 函数、目录、文件名使用小写下划线。
- 函数签名必须有类型注解。
- 输入输出优先使用 Pydantic 模型。
- 路由层只做参数接收和响应返回，不写复杂业务逻辑。
- 服务层负责业务流程编排。
- 仓储层负责数据库读写。
- 工具函数尽量保持纯函数。
- 错误优先处理，使用早返回，避免深层嵌套。
- 所有模块必须有单元测试。

### 4.3 推荐目录结构

每个项目都尽量保持类似结构：

```text
project_name/
  app/
    __init__.py
    main.py
    api/
      __init__.py
      v1/
        __init__.py
        routes.py
        endpoints/
          __init__.py
    core/
      __init__.py
      config.py
      logging.py
      errors.py
    schemas/
      __init__.py
    services/
      __init__.py
    repositories/
      __init__.py
    models/
      __init__.py
    utils/
      __init__.py
  tests/
    __init__.py
  pyproject.toml
  README.md
  .env.example
```

不是每个项目都必须有 FastAPI。如果某个项目只是离线计算任务，可以没有 `app/main.py`，只保留 services、repositories、schemas、tests。

### 4.4 生产级项目流程

第一版虽然是 MVP，但必须按可上线项目管理，避免第二版推倒重来。每个项目都按以下流程推进：

```text
需求边界确认
  ↓
公共协议设计
  ↓
数据库 schema 与 migration 设计
  ↓
服务 / 仓储 / 路由实现
  ↓
单元测试 / 集成测试 / 契约测试
  ↓
本地验收与样例数据回放
  ↓
灰度发布或离线批任务试运行
  ↓
生产监控、日志、审计与回滚方案
```

每个阶段必须有明确产物：

- 需求边界：当前项目“做什么”和“明确不做什么”。
- 公共协议：Pydantic schema、枚举、错误类型、版本策略。
- 数据库变更：SQLAlchemy model、Alembic migration、唯一约束、索引、回滚脚本。
- 实现：路由层、服务层、仓储层职责分离。
- 测试：`python -m unittest` 通过，并覆盖边界条件。
- 验收：固定样例数据可以复现结果。
- 发布：配置、日志、指标、错误告警、回滚路径齐全。

### 4.5 服务边界硬约束

- 业务项目之间不能直接 import 对方的内部代码、SQLAlchemy model、repository 或 service。
- 跨项目共享结构只能来自 `quant_contracts`。
- 跨项目调用优先通过 HTTP API、批量数据快照、消息队列或只读数据视图。
- 每个项目只能写入自己拥有的数据表；读取其他项目数据必须走明确授权的只读接口或只读视图。
- 路由层不能直接访问数据库，数据库读写必须放在 repositories 层。
- services 层负责业务流程编排，不直接拼接 SQL。
- factors、metrics、rules 等核心计算函数尽量保持纯函数，便于单元测试和复现。
- 新增服务必须有 README，说明职责边界、输入输出、运行方式、测试方式和不负责事项。

### 4.6 接口与数据兼容策略

- HTTP API 从 `/api/v1` 开始，破坏性变更必须新增 `/api/v2`。
- Pydantic schema 优先做向后兼容变更：允许新增可选字段，不随意删除、重命名或改变字段含义。
- 数据库字段变更优先使用增量 migration：先加字段，再回填，再切换读取逻辑，最后考虑删除旧字段。
- 对外输出的枚举值不能随意改名；如必须废弃，先保留兼容期并在 README 中说明。
- 生产数据必须保留 `created_at`、`updated_at`，关键结果必须保留 `run_id` 或可追踪的批次标识。

### 4.7 数据血缘与可审计约束

- 所有行情、因子、验证报告都必须能追溯到数据来源、数据版本、计算版本和运行批次。
- 所有批处理任务必须生成 `run_id`，并记录输入参数、时间范围、代码版本、数据版本和输出位置。
- 因子和验证结果必须能用固定输入数据复现。
- 禁止在计算函数中隐式读取当前日期、当前数据库最新值或外部状态；这些都必须作为显式参数传入。
- 涉及未来收益、调仓、成交价格的逻辑必须写明时间窗口，禁止未来函数。

### 4.8 测试与验收约束

- 所有项目统一使用 `unittest`。
- 纯函数必须有小样本确定性测试。
- repository 必须覆盖唯一约束、重复写入、空数据、非法数据。
- API 必须覆盖成功响应、参数错误、空结果、权限或配置错误。
- 因子、验证、回测必须有固定样例数据，结果改动必须能解释。
- 生产发布前必须至少通过：

```text
python -m unittest
ruff check .
```

`mypy` 第一阶段暂不作为全仓库强制门禁。后续先从 `quant_contracts` 和 `quant_data_sdk` 这类公共协议/SDK 层启用，再逐步覆盖因子计算和验证服务。

### 4.9 Redis 缓存、幂等与运行状态约束

Redis 从第一版开始作为缓存层和轻量协调层启用，但不作为任何业务数据的最终事实来源。

适用场景：

| 场景 | 推荐位置 | 典型用途 |
| ---- | ---- | ---- |
| 元数据缓存 | `quant_data_hub` | 交易日历、证券主数据、复权批次、数据版本摘要 |
| 查询短缓存 | `quant_data_hub` / `quant_ops_api` | 小范围行情查询、Dashboard 聚合、报告预览 |
| 任务幂等 | `quant_factor_lab` / `quant_factor_validation` | `run_id` 级别分布式锁、重复提交保护、任务状态 |
| 外部访问控制 | 数据接入 adapter / API gateway | 第三方 API 请求去重、限流、短期响应缓存 |

推荐 key 设计：

```text
calendar:{market}:{year}
security:{symbol}
qfq_batch:{batch_id}
market_bars:{symbol}:{timeframe}:{price_mode}:{start}:{end}:{data_version}
ops:overview:{version}
ops:factor_validation:latest
lock:factor_calc:{run_id}
lock:validation:{run_id}
task_status:{run_id}
```

强约束：

- Redis 不保存永久业务真相，不替代 PostgreSQL、ClickHouse 或 MinIO。
- 大规模行情、完整因子矩阵、验证明细序列不直接塞 Redis。
- 缓存 key 必须包含 `data_version`、`batch_id`、`run_id` 等可复现字段。
- 缓存失效优先使用版本化 key 和 TTL，不依赖手工批量删除。
- 分布式锁使用 `SET key value NX EX seconds` 语义，并设置合理过期时间。
- Redis 访问必须放在 cache、repository、integration 或 adapter 层，路由层不能直接操作 Redis。

### 4.10 配置、密钥与运行约束

- 所有配置通过环境变量或配置文件注入，仓库只保留 `.env.example`。
- 不允许在代码、测试、notebook、README 中写入真实数据库密码、API token 或券商密钥。
- 第三方数据源、数据库、Redis、消息队列都必须通过依赖注入或配置对象初始化。
- 外部 I/O 默认使用异步实现；确实需要同步库时，必须隔离在 repository 或 adapter 层。
- 生产服务必须有结构化日志，日志中保留 `request_id`、`run_id` 或任务批次号。
- 容器部署与服务编排详见 `docs/container_deployment_and_orchestration.md`。

### 4.11 公共 GitHub 仓库约束

可以使用公共 GitHub 仓库统一管理代码，但仓库只能保存：

```text
代码
文档
测试
Alembic migration
ClickHouse DDL
Dockerfile / docker-compose 样例
.env.example
小样本 fixture
```

禁止提交：

```text
.env
真实 token / 密码 / secret
PostgreSQL 数据目录
ClickHouse 数据目录
MinIO 数据目录
真实行情大文件
数据库 dump
日志文件
```

推荐仓库结构：

```text
packages/
  quant_contracts/
services/
  quant_data_hub/
  quant_factor_lab/
  quant_factor_validation/
clients/
  quant_data_sdk/
infra/
  local/
  remote_101/
docs/
  references/
```

GitHub Actions 第一阶段只运行不依赖真实密钥和外部数据的检查：

```text
python -m unittest
ruff check .
docker compose config
```

---

## 5. 公共协议项目：quant_contracts

### 5.1 项目定位

`quant_contracts` 是所有项目的公共语言。它不连接数据库，不计算因子，不做回测，只定义共享结构。

职责：

- 公共 Pydantic schema
- 公共枚举
- 公共错误类型
- 公共时间、代码格式、市场类型定义
- 通用响应结构

不负责：

- 不连接 PostgreSQL
- 不连接 Redis
- 不实现业务计算
- 不包含 FastAPI 路由
- 不读取第三方数据

### 5.2 推荐目录

```text
quant_contracts/
  quant_contracts/
    __init__.py
    enums/
      __init__.py
      market.py
      frequency.py
      asset.py
    schemas/
      __init__.py
      market_data.py
      factor.py
      signal.py
      portfolio.py
      backtest.py
      risk.py
      common.py
    errors/
      __init__.py
      base.py
    utils/
      __init__.py
      symbol.py
      trading_date.py
  tests/
    test_market_data_schema.py
    test_factor_schema.py
  pyproject.toml
  README.md
```

### 5.3 核心 schema 示例

```python
from datetime import date, datetime
from pydantic import BaseModel, Field


class MarketDailyBar(BaseModel):
    symbol: str = Field(..., description="证券代码，例如 000001.SZ")
    trade_date: date
    open_price: float
    high_price: float
    low_price: float
    close_price: float
    pre_close_price: float | None = None
    volume: float = Field(..., description="成交量")
    turnover: float = Field(..., description="成交额")
    is_suspended: bool = False
    created_at: datetime | None = None


class FactorDailyValue(BaseModel):
    symbol: str
    trade_date: date
    factor_name: str
    factor_value: float | None
    universe_name: str | None = None


class FactorValidationMetric(BaseModel):
    factor_name: str
    start_date: date
    end_date: date
    ic_mean: float | None = None
    rank_ic_mean: float | None = None
    ic_ir: float | None = None
    long_short_return: float | None = None
    coverage_ratio: float | None = None
    missing_ratio: float | None = None


class TradingSignal(BaseModel):
    symbol: str
    trade_date: date
    signal_name: str
    signal_score: float
    target_weight: float | None = None


class TargetPosition(BaseModel):
    symbol: str
    trade_date: date
    target_weight: float
    reason: str | None = None
```

### 5.4 给 Codex 的提示词

```text
请为 quant_contracts 项目生成基础代码。

项目定位：
这是量化研究平台的公共协议项目，只负责定义 Pydantic v2 schema、枚举、错误类型和少量纯工具函数。

技术要求：
1. 使用 Python 3.12。
2. 使用 Pydantic v2。
3. 不允许连接数据库。
4. 不允许包含 FastAPI 路由。
5. 不允许实现因子计算、回测、风控、模型训练等业务逻辑。
6. 所有函数和模型字段必须有类型注解。
7. 文件和目录使用小写下划线。
8. 使用 unittest 编写测试。

需要生成：
1. quant_contracts/enums/market.py
2. quant_contracts/enums/frequency.py
3. quant_contracts/enums/asset.py
4. quant_contracts/schemas/market_data.py
5. quant_contracts/schemas/factor.py
6. quant_contracts/schemas/signal.py
7. quant_contracts/schemas/portfolio.py
8. quant_contracts/schemas/backtest.py
9. quant_contracts/schemas/risk.py
10. quant_contracts/errors/base.py
11. tests 下的基础单元测试
12. pyproject.toml
13. README.md

验收标准：
1. python -m unittest 可以通过。
2. 所有 schema 可以正常实例化。
3. 对非法字段能触发 Pydantic 校验错误。
4. 业务项目可以通过 pip install -e ../quant_contracts 引用。
```

---

## 6. 数据接入项目：quant_data_hub

### 6.1 项目定位

`quant_data_hub` 专门负责数据接入、清洗、标准化、存储、查询和数据血缘。

结合 101 旧项目验证结果，`quant_data_hub` 的生产形态不应只依赖 PostgreSQL，而应采用：

```text
PostgreSQL  # 控制面：元数据、任务、导入记录、血缘、小规模验证表
ClickHouse  # 行情分析主存储：raw/qfq/hfq 查询、日线/分钟线大表
MinIO       # 原始文件、导入中间产物、研究结果和报告
Redis       # 元数据缓存、查询短缓存、任务幂等和运行状态
```

职责：

- 接收第三方行情数据
- 清洗字段名和数据类型
- 统一股票代码格式
- 处理交易日
- 处理停牌、缺失值、复权价格
- 写入 PostgreSQL 控制面
- 写入 ClickHouse 行情分析表
- 写入或登记 MinIO 对象
- 使用 Redis 缓存高频元数据和短期查询结果
- 提供标准查询 API
- 提供 qfq / hfq 价格口径查询
- 记录导入任务和研究产物血缘

不负责：

- 不计算因子
- 不做因子有效性判断
- 不做模型训练
- 不做回测
- 不做风控

### 6.2 输入输出

输入：

```text
第三方行情数据
CSV / Excel / API / 数据库同步数据
```

输出：

```text
market_daily_bar
security_master
trading_calendar
ClickHouse raw/qfq/hfq 行情表
MinIO 原始文件和研究产物对象
Redis 元数据缓存和短期查询缓存
```

### 6.3 推荐数据表

PostgreSQL 适合保存控制面和小规模验证表。日线 MVP 可先保留 `market_daily_bar`，但大规模行情查询应优先落到 ClickHouse。

```sql
create table market_daily_bar (
    id bigserial primary key,
    symbol varchar(32) not null,
    trade_date date not null,
    open_price numeric(20, 6) not null,
    high_price numeric(20, 6) not null,
    low_price numeric(20, 6) not null,
    close_price numeric(20, 6) not null,
    pre_close_price numeric(20, 6),
    volume numeric(24, 6) not null,
    turnover numeric(24, 6) not null,
    is_suspended boolean not null default false,
    data_source varchar(64) not null,
    data_version varchar(128),
    source_updated_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(symbol, trade_date)
);

create index idx_market_daily_bar_trade_date on market_daily_bar(trade_date);
create index idx_market_daily_bar_symbol on market_daily_bar(symbol);
```

101 旧项目中已经验证过的 ClickHouse 表结构可作为生产参考：

```text
market_data_1d_raw
market_data_1m_raw
market_data_5m_raw
adjustment_factors
qfq_batches
market_data_1d_qfq_cache
market_data_1m_qfq_cache
market_data_5m_qfq_cache
v_market_data_1d_hfq
v_market_data_1m_hfq
v_market_data_5m_hfq
```

101 PostgreSQL 中的 `market_data_1d`、`market_data_1m`、`market_data_5m` 是采集期宽表：同一张表同时保存 raw 价格、`qfq_*` 前复权价格、`hfq_*` 后复权价格、`adj_factor`、`qfq_factor`、`hfq_factor` 和 `qfq_base_date`。该结构可以作为历史兼容、迁移校验和小规模回放参考，但不建议照搬为生产分析主表。

生产查询层采用以下口径：

```text
ClickHouse raw table
  保存原始价格、成交量、成交额、源 adj_factor / hfq_factor

ClickHouse qfq cache table
  按 batch_id + qfq_base_date 生成前复权价格
  raw 表不被覆盖

ClickHouse hfq view
  基于 raw price * hfq_factor 动态提供后复权价格

quant_contracts MarketBarsResponse.meta
  返回 price_mode、batch_id、qfq_base_date 等复权元数据
```

对因子服务暴露的 `MarketBar.adjustment_factor` 表示当前 `price_mode` 下生效的复权因子：raw 为源 `adj_factor`，qfq 为 `qfq_factor`，hfq 为 `hfq_factor`。因子计算只消费一种明确价格口径，不能在同一次计算中隐式混用 raw/qfq/hfq 三套价格。

详细 DDL 参考：

```text
docs/references/legacy_data_ingestion/deploy/clickhouse/initdb/001_market_data.sql
```

### 6.4 推荐 API

```text
POST /api/v1/market-bars/batch-upsert
GET  /api/v1/market-bars?symbol=000001.SZ&start_date=2024-01-01&end_date=2024-12-31
GET  /api/v1/trading-calendar?start_date=2024-01-01&end_date=2024-12-31
POST /api/v1/market/bars/query
GET  /api/v1/adjustments/qfq-batches
```

### 6.5 生产数据约束

- `quant_data_hub` 是第三方原始行情数据进入主链路的唯一入口。
- 第三方字段映射、证券代码标准化、交易日处理、停复牌处理、复权口径都必须在 `quant_data_hub` 内完成。
- Tushare 可作为真实测试数据源和后续生产 ingestion source，但 token、订单号、购买权限信息只能通过本机 `.env`、shell 环境变量或部署密钥管理注入，不能进入代码、README、测试 fixture 或 Git 历史。
- Tushare SDK 只能出现在 `quant_data_hub` ingestion / integration adapter 或本地 smoke 脚本中，不能进入 `quant_factor_lab` 的因子纯函数、算法 adapter 执行路径或 `quant_factor_validation` 的指标函数。
- 使用 Tushare 做 qfq 测试时必须同时读取并校验 `adj_factor`，缺少复权因子时测试应失败，不能用 raw price 冒充前复权口径。
- 批量写入必须幂等，同一 `symbol + trade_date` 重复导入不能生成重复记录。
- 每次导入必须记录 `data_source`、`data_version`、`source_updated_at` 和导入批次。
- 对外提供数据时必须支持明确的时间范围，后续回测和因子计算不能隐式读取“当前最新全量数据”。
- 如果供应商数据存在修订，必须保留可审计的版本记录或导入日志，便于复现历史研究结果。
- 大规模日线、分钟线行情主查询层优先使用 ClickHouse。
- qfq 前复权依赖 `batch_id` 和 `qfq_base_date`，不能覆盖 raw 主表。
- hfq 后复权可以使用 ClickHouse view 动态计算。
- MinIO 只通过服务端预签名 URL 或受控 SDK 暴露，不向研究员暴露管理密钥。
- Redis 只缓存交易日历、证券主数据、复权批次元数据和小范围查询结果，不保存行情主数据。
- Redis key 必须包含 `data_version`、`batch_id` 或明确时间范围，避免供应商修订后读到旧口径。
- 101 旧项目重合分析见 `docs/legacy_data_ingestion_overlap_and_migration.md`。
- 旧字段到 `quant_contracts` 的映射见 `docs/quant_contracts_legacy_mapping.md`。

### 6.6 给 Codex 的提示词

```text
请为 quant_data_hub 项目生成基础代码。

项目定位：
该项目是量化研究平台的数据接入层，只负责行情数据接入、清洗、标准化、入库、查询和数据血缘。

强约束：
1. 该项目依赖 quant_contracts。
2. 只处理数据，不计算因子。
3. 不做回测。
4. 不做模型训练。
5. 不做风控。
6. 使用 FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + asyncpg。
7. PostgreSQL 用作控制面，ClickHouse 用作行情分析主存储，MinIO 用作对象存储。
8. 测试使用 unittest。
9. Redis 用作元数据缓存和短期查询缓存，不作为主存储。
10. 所有 PostgreSQL / ClickHouse / MinIO / Redis 操作必须放在 repositories、cache 或 integrations 层。
11. 路由层不能直接访问数据库或 Redis。

需要生成：
1. app/main.py
2. app/core/config.py
3. app/core/database.py
4. app/core/errors.py
5. app/api/v1/routes.py
6. app/api/v1/endpoints/market_bars.py
7. app/models/market_daily_bar.py
8. app/repositories/market_bar_repository.py
9. app/services/market_bar_service.py
10. app/schemas/market_bar.py
11. tests/test_market_bar_service.py
12. tests/test_market_bar_repository.py
13. .env.example
14. pyproject.toml
15. README.md

业务要求：
1. 实现批量 upsert 日频行情数据。
2. 按 symbol + trade_date 做唯一约束。
3. 支持按 symbol、start_date、end_date 查询行情。
4. 对非法日期、空 symbol、价格小于 0、成交量小于 0 做校验。
5. 写入时记录 data_source、data_version、source_updated_at。
6. 返回结构使用统一响应模型。

验收标准：
1. python -m unittest 可以通过。
2. FastAPI 能启动。
3. 批量 upsert 重复数据不会重复插入。
4. 查询接口返回结构符合 quant_contracts 中的 MarketDailyBar。
```

---

## 7. 因子计算项目：quant_factor_lab

### 7.1 项目定位

`quant_factor_lab` 只负责把标准化后的行情数据或研究数据快照转换成因子值。

职责：

- 读取 `quant_data_hub` 输出的标准行情数据
- 读取经批准的只读研究数据快照
- 计算量价因子
- 计算截面因子
- 做基础去极值、标准化、中性化，第一版可先预留接口
- 存储因子值
- 使用 Redis 做 `run_id` 幂等锁和短期行情窗口缓存

不负责：

- 不判断因子是否有效
- 不做完整回测
- 不做交易执行
- 不负责第三方原始行情接入、清洗、代码映射、复权口径定义和数据质量判定
- 不把完整因子矩阵或长期研究产物写入 Redis

### 7.1.1 第三方原始数据兼容策略

生产主链路不允许 `quant_factor_lab` 直接依赖第三方原始数据源。标准链路必须是：

```text
第三方数据源
    ↓
quant_data_hub 接入、清洗、标准化、入库或生成快照
    ↓
quant_factor_lab 读取标准数据并计算因子
```

为了支持早期研究、供应商切换、另类数据探索，可以允许兼容读取第三方原始数据，但必须满足以下约束：

- 只能通过只读 `data_provider` / `adapter` 读取，不能在因子函数中直接调用第三方 SDK 或 API。
- adapter 必须把第三方字段转换成 `quant_contracts` 中的标准 schema，或转换成项目内明确的 Pydantic 输入模型。
- 第三方原始字段名不能进入 `app/factors/` 的纯计算函数。
- adapter 不能负责正式入库、复权口径定义、证券代码主数据维护或数据质量判定。
- 第三方数据读取必须通过配置开关启用，默认生产配置关闭。
- 读取结果必须记录 `data_source`、`data_version`、`run_id` 和时间范围。
- 如果某个第三方数据源进入生产主链路，必须迁移到 `quant_data_hub` 或单独的数据接入项目维护。

允许的兼容结构：

```text
app/repositories/providers/
  third_party_market_data_provider.py   # 只读 adapter
  market_data_provider.py               # 抽象接口
```

不允许的结构：

```text
app/factors/momentum.py 直接调用第三方 API
app/services/factor_calculation_service.py 直接解析供应商原始字段
quant_factor_lab 写入 raw_market_data 表
```

### 7.2 因子分类口径

后续不要只用“股票 / 期货”区分因子，而要在公共协议中同时固定三个维度：

```text
asset_class     # equity / futures
factor_mode     # cross_sectional / time_series
factor_family   # price_volume / term_structure / fundamental / macro / model
```

建议口径：

| 资产 | 因子形态 | 因子族 | 典型因子 | 默认验证方向 |
| ---- | ---- | ---- | ---- | ---- |
| 股票 | `cross_sectional` | `price_volume` | 动量、反转、波动率、量比、价量相关 | IC、Rank IC、分组收益、多空收益、换手 |
| 股票 | `cross_sectional` | `fundamental` | 估值、盈利、成长、质量、资产定价特征 | 截面 IC、分组收益、行业/市值中性后表现 |
| 股票 | `cross_sectional` | `model` | ML alpha score、模型预测收益 | train/valid/test、IC、Rank IC、组合回测 |
| 期货 | `time_series` | `price_volume` | TSMOM、突破、均线、成交量冲击、波动率状态 | 单品种时序回测、Sharpe、回撤、胜率、换手 |
| 期货 | `cross_sectional` | `term_structure` | carry、期限结构 slope/curvature、跨品种动量 XSMOM | 跨品种排序、分组收益、Rank IC、板块中性 |

第一版当前只把股票日频量价截面因子放进生产主链路。期货时序因子、期货截面因子和股票 ML alpha 暂不进入 MVP，但协议从第一版开始预留，避免第二版重做字段和数据接口。

### 7.3 外部库在因子计算层的定位

外部库不作为 `quant_factor_lab` 的统一底座，而是按研究方向作为参考实现、benchmark 或 adapter 接入。生产因子值仍以 `quant_contracts` 定义的结构为准。

| 库 / 项目 | 适用方向 | 在当前项目中的角色 |
| ---- | ---- | ---- |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | 股票截面研究流水线、Alpha158 / Alpha360、后续模型研究 | 参考 Data Handler、Dataset、Processor 分层，不直接替代 `quant_data_hub` |
| [Qlib Alpha158 / Alpha360](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md) | 股票 engineered factors 和 raw window features | 作为因子模板和特征窗口设计参考 |
| [OpenSourceAP/CrossSection](https://github.com/OpenSourceAP/CrossSection) | 股票基本面和资产定价截面因子 | 参考因子定义、复现实验结构和字段口径 |
| [commodity-curve-factors](https://github.com/brianbanna/commodity-curve-factors) | 商品期货期限结构、carry、slope、curvature、TSMOM / XSMOM | 参考期货时序和截面因子形态 |
| [vectorbt](https://github.com/polakowo/vectorbt) | 大规模时序策略和参数实验 | 参考期货时序量价因子回测，不作为交易执行引擎 |

强约束：

- 外部库输出必须映射回标准 factor schema，不能把第三方私有字段直接写进核心表。
- 如果两个库都能计算同类结果，可以并行输出到 `evaluation_engine_result` 做对比，但生产主结论必须经过统一评分和审核。
- `quant_factor_lab` 只产出因子值，不负责判断哪个库“更好”。
- Redis 只能缓存短期行情窗口、计算状态和幂等锁，不能作为因子值主存储。

### 7.4 第一批建议实现的因子

建议先实现简单、可解释、容易验证的基础因子：

```text
momentum_20d              # 20 日动量
reversal_5d               # 5 日反转
volatility_20d            # 20 日收益率波动率
volume_ratio_20d          # 当日成交量 / 20 日平均成交量
turnover_change_20d       # 换手变化，可后续做
price_volume_corr_20d     # 20 日价量相关性
```

### 7.5 推荐数据表

```sql
create table factor_daily_value (
    id bigserial primary key,
    run_id varchar(64) not null,
    symbol varchar(32) not null,
    trade_date date not null,
    factor_name varchar(128) not null,
    factor_value numeric(24, 10),
    universe_name varchar(128) not null default 'default',
    data_source varchar(64) not null default 'quant_data_hub',
    data_version varchar(128),
    factor_version varchar(64) not null default 'v1',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique(run_id, symbol, trade_date, factor_name, universe_name)
);

create index idx_factor_daily_value_factor_date on factor_daily_value(factor_name, trade_date);
create index idx_factor_daily_value_symbol on factor_daily_value(symbol);
create index idx_factor_daily_value_run_id on factor_daily_value(run_id);
```

### 7.6 给 Codex 的提示词

```text
请为 quant_factor_lab 项目生成基础代码。

项目定位：
该项目是量化研究平台的因子计算层，只负责从标准行情数据或经批准的只读数据快照中计算因子值，并写入 factor_daily_value。

强约束：
1. 依赖 quant_contracts。
2. 生产默认只读取 quant_data_hub 或标准数据快照。
3. 如需兼容第三方原始数据，只能通过只读 provider adapter，并且必须先转换成标准 schema。
4. 不负责第三方原始数据的清洗、代码映射、复权口径、入库和数据质量判定。
5. 不实现因子有效性验证。
6. 不实现完整回测。
7. 不实现模型训练。
8. 不实现风控和交易执行。
9. 因子计算函数尽量使用纯函数。
10. 数据库访问必须通过 repositories 层。
11. 使用 Pydantic v2 定义输入输出。
12. 使用 unittest。
13. 因子必须标注 asset_class、factor_mode、factor_family。
14. 外部库结果只能通过 adapter 映射到标准 schema。
15. Redis 只用于 run_id 幂等锁和短期窗口缓存，不能保存长期因子矩阵。

需要生成：
1. app/schemas/factor_request.py
2. app/models/factor_daily_value.py
3. app/repositories/market_data_reader.py
4. app/repositories/factor_value_repository.py
5. app/services/factor_calculation_service.py
6. app/factors/momentum.py
7. app/factors/reversal.py
8. app/factors/volatility.py
9. app/factors/volume_ratio.py
10. app/factors/price_volume_corr.py
11. tests/test_momentum.py
12. tests/test_reversal.py
13. tests/test_volatility.py
14. tests/test_factor_calculation_service.py
15. README.md

第一批因子：
1. momentum_20d = close_price / close_price.shift(20) - 1
2. reversal_5d = -(close_price / close_price.shift(5) - 1)
3. volatility_20d = rolling_std(daily_return, 20)
4. volume_ratio_20d = volume / rolling_mean(volume, 20)
5. price_volume_corr_20d = rolling_corr(daily_return, volume_change, 20)

验收标准：
1. 给定一组固定测试行情，因子计算结果可复现。
2. 缺少足够窗口期时返回 None 或 NaN，并在写库前统一处理。
3. 不允许未来函数，计算 T 日因子时不能使用 T+1 之后数据。
4. python -m unittest 可以通过。
```

---

## 8. 因子验证项目：quant_factor_validation

### 8.1 项目定位

`quant_factor_validation` 是判断因子是否可用的核心项目。

职责：

- 读取因子值
- 读取未来收益
- 计算 IC
- 计算 Rank IC
- 计算 ICIR
- 分组收益
- 多空收益
- 覆盖率
- 缺失率
- 换手率
- 输出因子验证报告
- 使用 Redis 缓存验证摘要、报告预览和 `run_id` 幂等锁

不负责：

- 不计算原始因子
- 不负责数据接入
- 不做实盘交易
- 不做复杂组合优化
- 不直接训练用于生产准入判断的黑盒模型
- 不把完整验证明细、IC 序列长期存入 Redis

### 8.2 核心指标

```text
IC：因子值与未来收益的相关性
Rank IC：因子排序与未来收益排序的相关性
ICIR：IC 均值 / IC 标准差
分组收益：按因子分成 5 组或 10 组，看高分组是否优于低分组
多空收益：最高分组收益 - 最低分组收益
覆盖率：有效因子值数量 / 股票池数量
缺失率：缺失因子值数量 / 股票池数量
换手率：组合持仓变化程度
```

### 8.3 验证引擎与评分协议

`quant_factor_validation` 的第一目标是形成统一评价口径。无论结果来自自研验证、Alphalens、Qlib、vectorbt，还是其他研究库，都必须先映射成标准协议，再进入评分和审核。

建议新增或预留以下协议：

```text
EvaluationEngine           # internal / alphalens / qlib / vectorbt / opensource_ap / commodity_curve
ExternalFactorValidationSummary
FactorEvaluationResult     # 单个验证引擎的标准化结果
FactorScoreCard            # 可解释评分卡
FactorComparisonReport     # 多引擎对比报告
```

不同场景的默认对照关系：

| 场景 | 默认验证 | 可选对照库 |
| ---- | ---- | ---- |
| 股票量价截面因子 | internal validation | Alphalens、Qlib |
| 股票基本面/资产定价因子 | internal validation | OpenSourceAP/CrossSection、Qlib |
| 股票 ML alpha | Qlib、internal validation | MLflow 记录实验 |
| 期货时序量价因子 | internal backtest | vectorbt |
| 期货截面/期限结构因子 | internal validation | commodity-curve-factors |

第一版评分先使用透明规则，不直接使用模型替代审核：

```text
final_score =
  rank_ic_ir_score
  + group_return_score
  + stability_score
  + turnover_penalty
  + coverage_score
  + drawdown_penalty
```

这个分数只能帮助排序和复核，不能单独决定生产准入。生产准入仍需要 `review_decision`、`reviewer_notes`、`approved_by` 和可追溯的任务/产物记录。

### 8.4 推荐输出

```text
factor_validation_report
factor_ic_series
factor_group_return_series
factor_long_short_return_series
factor_evaluation_result
factor_score_card
factor_comparison_report
```

### 8.5 给 Codex 的提示词

```text
请为 quant_factor_validation 项目生成基础代码。

项目定位：
该项目用于验证因子是否有效。输入是 factor_daily_value 和 market_daily_bar，输出是因子评价指标和验证报告。

强约束：
1. 依赖 quant_contracts。
2. 不计算原始因子。
3. 不接入第三方原始数据。
4. 不做交易执行。
5. 不做复杂机器学习模型。
6. 指标计算函数尽量使用纯函数。
7. 禁止未来函数：计算未来收益时必须明确 forward_return_n 的窗口。
8. 使用 unittest。
9. 外部验证库输出必须先映射成 FactorEvaluationResult。
10. 规则评分必须输出每个 score component，不能只输出 final_score。
11. Redis 只用于验证任务锁、报告预览和短期聚合缓存，正式产物仍写入 MinIO / PostgreSQL。

需要生成：
1. app/schemas/validation_request.py
2. app/schemas/validation_result.py
3. app/repositories/factor_reader.py
4. app/repositories/market_data_reader.py
5. app/services/factor_validation_service.py
6. app/metrics/ic.py
7. app/metrics/rank_ic.py
8. app/metrics/group_return.py
9. app/metrics/long_short_return.py
10. app/metrics/coverage.py
11. app/metrics/turnover.py
12. tests/test_ic.py
13. tests/test_rank_ic.py
14. tests/test_group_return.py
15. tests/test_factor_validation_service.py
16. README.md

业务要求：
1. 支持 forward_days 参数，例如 1、5、10、20。
2. 支持 group_count 参数，例如 5 或 10。
3. 支持按日期横截面计算 IC 和 Rank IC。
4. 支持输出每日 IC 序列。
5. 支持输出总体 ic_mean、rank_ic_mean、ic_std、ic_ir。
6. 支持输出分组收益曲线。
7. 支持输出多空收益曲线。
8. 支持覆盖率和缺失率统计。

验收标准：
1. 使用固定小样本数据可以得到可复现的 IC 结果。
2. 分组收益计算不能使用未来因子值。
3. 对全空因子、常数因子、样本不足等边界情况有明确处理。
4. python -m unittest 可以通过。
```

---

## 9. 模型项目：quant_model_lab

### 9.1 项目定位

`quant_model_lab` 负责把多个因子合成为交易信号。

第一阶段可以先不做复杂机器学习，先做简单规则：

```text
因子标准化 → 因子方向调整 → 等权合成 → 输出 signal_score
```

后续再扩展：

```text
IC 加权
线性回归
Ridge / Lasso
LightGBM
XGBoost
时间序列模型
横截面排序模型
```

### 9.2 输入输出

输入：

```text
factor_daily_value
factor_validation_report
```

输出：

```text
signal_daily_value
```

### 9.3 给 Codex 的提示词

```text
请为 quant_model_lab 项目生成基础代码。

项目定位：
该项目负责因子组合和信号生成。第一阶段只实现简单、可解释的规则模型，不实现复杂机器学习。

强约束：
1. 依赖 quant_contracts。
2. 不计算原始因子。
3. 不做行情数据接入。
4. 不做完整回测。
5. 不做风控。
6. 第一阶段不要引入 LightGBM、XGBoost、深度学习。
7. 所有信号生成逻辑必须可解释。
8. 使用 unittest。

需要生成：
1. app/schemas/model_request.py
2. app/schemas/signal_result.py
3. app/repositories/factor_reader.py
4. app/repositories/signal_repository.py
5. app/services/signal_generation_service.py
6. app/models/equal_weight_model.py
7. app/models/ic_weight_model.py
8. app/preprocessing/winsorize.py
9. app/preprocessing/standardize.py
10. app/preprocessing/neutralize.py，可先留接口
11. tests/test_equal_weight_model.py
12. tests/test_standardize.py
13. tests/test_signal_generation_service.py
14. README.md

业务要求：
1. 支持多个因子输入。
2. 支持因子方向配置，例如 positive 或 negative。
3. 支持横截面 z-score 标准化。
4. 支持等权合成 signal_score。
5. 支持按日期输出股票排序。
6. 支持保存 signal_daily_value。

验收标准：
1. 小样本下信号合成结果可复现。
2. 缺失因子值有明确处理策略。
3. 因子方向调整正确。
4. python -m unittest 可以通过。
```

---

## 10. 回测项目：quant_backtest_engine

### 10.1 项目定位

`quant_backtest_engine` 负责将信号转成模拟持仓，并计算净值和绩效指标。

职责：

- 读取交易信号
- 生成目标持仓
- 模拟调仓
- 计算手续费和滑点
- 计算每日收益
- 输出净值曲线
- 输出最大回撤、年化收益、夏普比率等指标

不负责：

- 不计算原始因子
- 不训练模型
- 不接入第三方行情
- 不做实盘下单

### 10.2 核心配置

```text
start_date
end_date
initial_cash
rebalance_frequency
top_n
max_position_weight
fee_rate
slippage_rate
benchmark_symbol
```

### 10.3 给 Codex 的提示词

```text
请为 quant_backtest_engine 项目生成基础代码。

项目定位：
该项目是量化研究平台的回测引擎。输入是交易信号和行情数据，输出是持仓、成交、净值曲线和绩效指标。

强约束：
1. 依赖 quant_contracts。
2. 不计算原始因子。
3. 不做因子有效性验证。
4. 不训练模型。
5. 不执行真实交易。
6. 回测逻辑必须避免未来函数。
7. 使用 unittest。

需要生成：
1. app/schemas/backtest_request.py
2. app/schemas/backtest_result.py
3. app/repositories/signal_reader.py
4. app/repositories/market_data_reader.py
5. app/services/backtest_service.py
6. app/engine/portfolio.py
7. app/engine/rebalance.py
8. app/engine/order_simulator.py
9. app/engine/performance.py
10. app/engine/drawdown.py
11. tests/test_rebalance.py
12. tests/test_order_simulator.py
13. tests/test_performance.py
14. tests/test_backtest_service.py
15. README.md

业务要求：
1. 支持按日频回测。
2. 支持按 top_n 选股。
3. 支持等权持仓。
4. 支持手续费 fee_rate。
5. 支持滑点 slippage_rate。
6. 支持最大单票权重限制。
7. 输出 daily_nav、daily_return、positions、trades、metrics。
8. metrics 至少包含 total_return、annual_return、max_drawdown、sharpe_ratio、turnover。

验收标准：
1. 小样本回测结果可复现。
2. 调仓日和非调仓日逻辑正确。
3. 手续费和滑点计算正确。
4. 不允许使用未来价格成交。
5. python -m unittest 可以通过。
```

---

## 11. 风控项目：quant_risk_engine

### 11.1 项目定位

`quant_risk_engine` 负责对目标持仓进行约束和修正。

职责：

- 单票权重限制
- 行业权重限制
- 股票黑名单过滤
- 停牌过滤
- 涨跌停过滤
- 流动性过滤
- 最大回撤控制
- 换手率限制

不负责：

- 不计算因子
- 不生成原始信号
- 不做完整回测
- 不接入第三方原始行情

### 11.2 给 Codex 的提示词

```text
请为 quant_risk_engine 项目生成基础代码。

项目定位：
该项目负责对模型生成的目标持仓进行风控调整，输出风控后的目标持仓。

强约束：
1. 依赖 quant_contracts。
2. 不计算因子。
3. 不生成原始交易信号。
4. 不做完整回测。
5. 不执行真实交易。
6. 风控规则要模块化，每条规则单独实现和测试。
7. 使用 unittest。

需要生成：
1. app/schemas/risk_request.py
2. app/schemas/risk_result.py
3. app/services/risk_adjustment_service.py
4. app/rules/max_position_weight.py
5. app/rules/blacklist_filter.py
6. app/rules/suspended_filter.py
7. app/rules/limit_up_down_filter.py
8. app/rules/liquidity_filter.py
9. app/rules/turnover_limit.py
10. tests/test_max_position_weight.py
11. tests/test_blacklist_filter.py
12. tests/test_risk_adjustment_service.py
13. README.md

业务要求：
1. 输入 target_position 列表。
2. 按配置执行多条风控规则。
3. 输出 risk_adjusted_position。
4. 输出每个股票被调整的原因。
5. 支持规则开关。
6. 支持最大单票权重限制。
7. 支持黑名单过滤。
8. 支持停牌股票目标权重置零或保持原仓，策略可配置。

验收标准：
1. 每条风控规则有独立单元测试。
2. 多条规则叠加顺序明确。
3. 输出权重总和处理逻辑明确。
4. python -m unittest 可以通过。
```

---

## 12. 执行项目：quant_execution_gateway

### 12.1 项目定位

`quant_execution_gateway` 建议最后做。早期先实现模拟交易或纸面交易，不直接接实盘。

职责：

- 接收风控后的目标持仓
- 生成订单
- 模拟下单
- 记录订单状态
- 后续对接券商或交易系统接口

不负责：

- 不计算因子
- 不做模型训练
- 不做回测
- 不直接修改风控规则

### 12.2 给 Codex 的提示词

```text
请为 quant_execution_gateway 项目生成基础代码。

项目定位：
该项目负责模拟交易执行。当前阶段只做 paper trading，不接真实券商接口。

强约束：
1. 依赖 quant_contracts。
2. 不计算因子。
3. 不训练模型。
4. 不做回测。
5. 不直接发送真实订单。
6. 所有订单状态变化必须可追踪。
7. 使用 unittest。

需要生成：
1. app/schemas/order.py
2. app/schemas/execution_request.py
3. app/schemas/execution_result.py
4. app/services/order_generation_service.py
5. app/services/paper_execution_service.py
6. app/repositories/order_repository.py
7. app/models/order.py
8. app/enums/order_status.py
9. tests/test_order_generation_service.py
10. tests/test_paper_execution_service.py
11. README.md

业务要求：
1. 输入当前持仓和目标持仓。
2. 生成买入/卖出订单。
3. 支持订单状态：created、submitted、filled、cancelled、rejected。
4. 支持模拟成交价。
5. 记录订单创建时间、成交时间、成交数量、成交价格。

验收标准：
1. 订单生成逻辑可复现。
2. 订单状态流转合法。
3. 不包含任何真实交易接口调用。
4. python -m unittest 可以通过。
```

---

## 13. 研究工作区：quant_research_workspace

### 13.1 项目定位

这个项目用于临时研究，不放生产服务代码。

适合放：

```text
notebooks/
experiments/
reports/
scripts/
```

不适合放：

```text
生产 API
数据库核心模型
正式风控规则
交易执行逻辑
```

### 13.2 推荐用途

- 临时验证某个因子
- 画图
- 写研究报告
- 对比多个因子表现
- 分析回测结果
- 存放 Obsidian 或 Markdown 草稿

### 13.3 给 Codex 的提示词

```text
请为 quant_research_workspace 生成研究工作区结构。

项目定位：
该项目只用于临时研究、notebook、实验脚本和报告草稿，不作为生产服务。

强约束：
1. 不放核心生产逻辑。
2. 不定义正式数据库模型。
3. 不作为其他项目的依赖。
4. 可以读取其他项目输出的数据。
5. 所有实验脚本需要注明输入数据来源和输出结果位置。

需要生成：
1. notebooks/
2. experiments/
3. reports/
4. scripts/
5. README.md
6. .gitignore

验收标准：
1. 目录清晰。
2. README 说明该项目不是生产代码。
3. 示例 notebook 或脚本能读取因子验证结果并生成简单报告。
```

---

## 14. 推荐开发顺序

### 阶段 0：公共协议

```text
quant_contracts
```

目标：先确定所有项目之间怎么说话。

验收：

```text
所有核心 schema 定义完成
所有业务项目可以安装并引用 quant_contracts
基础单元测试通过
```

### 阶段 1：数据闭环

```text
quant_data_hub
```

目标：把标准行情数据稳定存入 PostgreSQL。

验收：

```text
能批量写入 market_daily_bar
能按 symbol/date 查询
能处理重复写入
能处理非法数据
```

### 阶段 2：因子计算

```text
quant_factor_lab
```

目标：计算第一批基础量价因子。

验收：

```text
至少 5 个基础因子可计算
结果写入 factor_daily_value
无未来函数
固定样本测试通过
```

### 阶段 3：因子验证

```text
quant_factor_validation
```

目标：判断因子是否有实际预测能力。

验收：

```text
能输出 IC / Rank IC / ICIR
能输出分组收益
能输出多空收益
能输出覆盖率和缺失率
```

### 阶段 4：简单信号与回测

```text
quant_model_lab
quant_backtest_engine
```

目标：从有效因子生成信号，并跑出净值曲线。

验收：

```text
能等权合成多个因子
能按 top_n 选股
能输出回测净值和绩效指标
```

### 阶段 5：风控和模拟执行

```text
quant_risk_engine
quant_execution_gateway
```

目标：在模拟环境中完整跑通交易链路。

验收：

```text
能限制单票权重
能过滤黑名单/停牌股票
能生成模拟订单
能记录订单状态
```

---

## 15. Codex 通用提示词模板

后续每次让 Codex 做任务，建议使用这个格式。

```text
你是一个 Python / FastAPI / SQLAlchemy 2.0 / Pydantic v2 专家。

当前项目：{项目名}
项目定位：{只做什么}
明确不做：{不做什么}

请只修改和本次任务相关的文件，不要重构无关代码。

代码要求：
1. Python 3.12。
2. 所有函数必须有类型注解。
3. 输入输出优先使用 Pydantic v2 模型。
4. 数据库访问必须在 repositories 层。
5. 业务流程在 services 层。
6. 路由层只负责 HTTP 参数和响应。
7. 错误优先处理，使用早返回。
8. 使用 unittest 添加或更新测试。
9. 不要引入未说明的新依赖。
10. 不要把其他项目的职责写进当前项目。

生产约束：
1. 不破坏已有 public API、Pydantic schema 和数据库字段含义。
2. 如需数据库变更，必须同时提供 SQLAlchemy model 更新和 Alembic migration。
3. 关键结果必须记录 run_id、数据来源、数据版本和计算版本。
4. 不允许跨项目 import 内部 service、repository、model。
5. 不允许在代码或测试中写入真实密钥、token、数据库密码。
6. 外部 I/O 必须隔离在 repository 或 adapter 层。
7. 错误信息要面向用户可理解，日志要保留排查所需上下文。

本次任务：
{具体任务}

验收标准：
1. {标准 1}
2. {标准 2}
3. python -m unittest 必须通过。
4. ruff check . 必须通过，除非当前项目尚未配置 ruff。

请先给出你计划修改的文件列表，再生成代码。
```

---

## 16. Codex 分阶段执行建议

不要一次给 Codex 一个大任务，例如：

```text
帮我生成完整量化交易平台。
```

这种很容易失控。

建议拆成小任务：

```text
第一步：只生成 quant_contracts 的 schema 和测试。
第二步：只生成 quant_data_hub 的行情表模型和 repository。
第三步：只生成 market_daily_bar 的批量 upsert service。
第四步：只生成 market_bars 查询接口。
第五步：只生成 momentum_20d 因子函数和测试。
第六步：只生成 factor_daily_value repository。
第七步：只生成 IC 计算函数和测试。
```

每一步都要求 Codex 说明：

```text
修改了哪些文件
为什么这样设计
如何运行测试
有哪些边界情况
```

---

## 17. 最小可行版本 MVP

第一版不要做成“大而全平台”。MVP 的目标是把生产级边界、公共协议和最小研究闭环先跑稳：

```text
1. quant_contracts
2. quant_data_hub
3. quant_factor_lab
4. quant_factor_validation
```

同时从第一版开始预留：

```text
quant_ops_api     # 只读聚合 API
quant_ops_web     # 服务状态、任务血缘、产物索引和验证报告展示
```

这两个项目是支撑层，不改变核心闭环优先级，也不直接写生产数据库或对象存储。

MVP 数据链路：

```text
CSV 或第三方数据
    ↓
quant_data_hub 入库 market_daily_bar
    ↓
quant_factor_lab 计算基础因子
    ↓
写入 factor_daily_value
    ↓
quant_factor_validation 计算 IC / Rank IC / 分组收益
    ↓
输出 Markdown / CSV / JSON 报告
```

MVP 因子范围：

| 资产 | 因子形态 | 第一批因子 | 说明 |
| ---- | ---- | ---- | ---- |
| 股票 | 截面量价因子 | `momentum_20d`、`reversal_5d`、`volatility_20d`、`volume_ratio_20d`、`price_volume_corr_20d` | 生产主链路优先落地 |
| 期货 | 时序量价因子 | TSMOM、突破、均线、波动率状态 | 第一版只预留协议，不进入主链路 |
| 期货 | 截面/期限结构因子 | carry、slope、curvature、XSMOM | 第一版只预留协议，不进入主链路 |

MVP 报告：

```text
因子名称
样本区间
覆盖率
缺失率
IC 均值
Rank IC 均值
ICIR
分组收益
多空收益
是否建议进入下一阶段回测
```

MVP 阶段使用库和参考边界：

| 能力 | 第一版处理方式 | 外部库状态 |
| ---- | ---- | ---- |
| 股票截面验证 | 先使用自研 `quant_factor_validation` | Alphalens / Qlib payload runner 边界已落地 |
| 因子模板 | 先实现少量可解释量价因子 | Qlib Alpha158 / Alpha360、OpenSourceAP/CrossSection 作为参考 |
| 期货时序因子 | 先定义协议和样例字段 | vectorbt payload runner 边界已落地 |
| 期货期限结构因子 | 先定义 continuous contract、roll rule、term structure 字段 | commodity-curve-factors 作为研究参考 |
| 实验沉淀 | 先使用 PostgreSQL + MinIO 记录任务和产物 | MLflow / Optuna / Evidently 放到第二阶段 |
| 缓存与幂等 | 第一版启用 Redis | 缓存元数据、Dashboard 摘要、报告预览、`run_id` 锁和任务状态 |

第一版协议清单与当前状态：

```text
AssetClass               # 已落地
FactorMode               # 已落地
FactorFamily             # 已落地
AlgorithmSpec            # 已落地，用于登记可用 / planned 算法
AlgorithmCapability      # 已落地，用于声明资产类别、因子模式、输出类型和支持频率
AlgorithmParameterSpec   # 已落地，用于声明算法参数和默认值
AlgorithmReviewGate      # 已落地，用于声明 planned -> available 的准入门槛
AlgorithmReviewGateEvidenceSubmission / Record / Response # 已落地，用于研究员提交 gate evidence
AlgorithmGatePromotionFinding / AlgorithmPromotionReadinessResponse # 已落地，用于只读评估算法是否具备晋级条件
EvaluationEngine         # 已落地，当前运行引擎为 internal
ExternalFactorValidationSummary # 已落地，用于外部库核心统计摘要标准化
FactorEvaluationResult   # 已落地
FactorScoreCard          # 已落地
FactorComparisonReport   # 已落地
```

当前代码已经完成上述第一阶段协议的基础落地，并在 `quant_factor_lab` 中建立 `FactorAlgorithmAdapter` / `FactorAlgorithmRegistry` 算法适配层。现有 `technical.momentum` 已作为可运行 adapter 注册；EGARCH、GJR-GARCH、APARCH 已作为 `planned` 波动率算法规格登记，并通过 `AlgorithmReviewGate` 暴露假设、数据、构造、未来函数、验证和运维门槛。`quant_factor_lab` 已提供 evidence preview / submit / list / review 接口，用于校验研究员提交的 gate evidence，并可写入 PostgreSQL `algorithm_review_gate_evidence` 表；review decision 只把证据标记为 `accepted` 或 `rejected`，不直接修改 gate 状态。当前已新增只读 promotion readiness 规则：registry 中已 `satisfied` 的 required gate 直接视为满足，缺失 gate 只有存在 `accepted` evidence 才可视为补齐，最新证据为 `rejected` 且没有 accepted evidence 时保持阻塞；该评估只输出 `promotable` / `blocked`，不会自动修改 `AlgorithmSpec.status`。`quant_factor_validation` 已输出 `internal` 引擎的 `FactorScoreCard`、`FactorEvaluationResult` 和 `FactorComparisonReport`。外部库已落地标准摘要 adapter 入口，并提供 Alphalens / Qlib / vectorbt payload runner 边界；`quant_factor_validation` 已提供多引擎 payload compare API，`quant_ops_api` 已提供 BFF preview / compare / evidence list / evidence review / promotion readiness 代理，并可优先通过只读 object-store adapter 读取 `factor_comparison_report.v1` 标准产物；`quant_ops_web` 已展示标准 `FactorComparisonReport`、artifact reference、algorithm review evidence 和 promotion readiness 摘要。当前已提供 101 ClickHouse 只读真实因子流转 smoke，并把 validation artifact 自动映射为 `technical.momentum / validation_evidence` gate evidence submit；Tushare SDK 本地真实小样本 smoke 入口也已预留。第三方库执行层尚未作为运行依赖接入。

---

## 18. 因子评分与模型化三阶段路线

后续扩展不是直接堆库或上模型，而是分三阶段推进。这样第一版不会推倒重来，第二版也能沿着同一套协议扩展。

### 18.1 第一阶段：统一协议 + 多引擎对比 + 规则评分

目标：让不同库和自研结果可比，先解决字段、指标、产物和审核口径问题。

当前实现状态：

```text
quant_contracts
    已定义 AssetClass / FactorMode / FactorFamily / EvaluationEngine
    已定义 AlgorithmSpec / AlgorithmCapability / AlgorithmParameterSpec
    已定义 AlgorithmReviewGate，用于 planned -> available 准入门槛
    已定义 AlgorithmReviewGateEvidenceSubmission / Record / Response / ListResponse
    已定义 AlgorithmGatePromotionFinding / AlgorithmPromotionReadinessResponse，用于只读晋级评估
    已定义 ExternalFactorValidationSummary
    已定义 FactorEvaluationResult / FactorScoreCard / FactorComparisonReport

quant_factor_lab
    已提供 GET /api/v1/algorithms 算法清单
    已建立 FactorAlgorithmAdapter / FactorAlgorithmRegistry
    已将 technical.momentum 迁入 registry adapter
    已登记 volatility.egarch / volatility.gjr_garch / volatility.aparch planned specs
    已为算法 registry 输出 hypothesis / data / construction / leakage / validation / operations review gates
    已提供 POST /api/v1/algorithms/review-gates/evidence/preview，校验 evidence 并返回 not_persisted record
    已提供 POST /api/v1/algorithms/review-gates/evidence，持久化 algorithm review evidence
    已提供 POST /api/v1/algorithms/review-gates/evidence/{evidence_id}/review，记录 accepted / rejected 审核决策
    已提供 GET /api/v1/algorithms/{algorithm_id}/review-gates/evidence，读取 algorithm review evidence
    已提供 GET /api/v1/algorithms/{algorithm_id}/promotion/readiness，只读评估 required gates 是否可晋级
    已通过 101 ClickHouse 真实日线小样本计算 momentum_1d
    已将真实 flow validation artifact 映射为 technical.momentum / validation_evidence gate evidence submit

quant_factor_validation
    已输出 internal validation 结果
    已提供 ExternalFactorValidationSummary -> FactorEvaluationResult adapter
    已提供 AlphalensMetricPayload -> AlphalensMetricSummary -> ExternalFactorValidationSummary payload runner
    已提供 QlibMetricPayload -> QlibMetricSummary -> ExternalFactorValidationSummary payload runner
    已提供 VectorbtMetricPayload -> VectorbtMetricSummary -> ExternalFactorValidationSummary payload runner
    已提供 ExternalPayloadEvaluationSet -> FactorComparisonReport 多引擎 payload 汇总层
    已提供 POST /api/v1/factors/external-payloads/compare
    已输出 score_card.json / comparison_report.json
    已输出透明 score components
    已通过 101 ClickHouse 真实日线小样本计算 IC / Rank IC / manifest preview
    已提供 make smoke-tushare-factor-sample，用于有本地 Tushare token 或兼容 HTTP 代理 Key 时拉取真实小样本并验证 momentum + IC 流程
    已通过 Tushare 代理 HTTP 模式拉取真实 A 股 daily + adj_factor，并完成 qfq MarketBar -> momentum_1d -> IC / Rank IC 内存链路
    101 节点 PostgreSQL schema + MinIO persisted smoke 已通过

quant_ops_api / quant_ops_web
    quant_ops_api 已提供 GET /api/v1/factor-lab/algorithms 只读代理
    quant_ops_web 已启用 Factor Lab 页面展示 available / planned AlgorithmSpec registry 和 review gates
    quant_ops_api 已提供 GET /api/v1/factor-lab/algorithms/{algorithm_id}/promotion/readiness 只读代理
    quant_ops_web 已展示算法晋级评估摘要，包括可晋级 / 阻塞状态与 required gates 完成数
    已展示 first-stage score preview
    已通过 GET /api/v1/factor-validation/external-payloads/preview 提供只读多引擎 payload 对比预览
    preview 响应已携带 factor_comparison_report.v1 artifact_reference
    preview 已具备只读 object-store adapter，优先读取标准 comparison_report.json，失败时回退 BFF MVP payload
    preview 响应已携带 artifact_read_status / artifact_read_reason，用于区分 artifact_loaded 与 preview_fallback
    已提供 smoke-quant-ops-api-comparison-artifact，只读验证 comparison_report artifact 加载状态
    已通过 POST /api/v1/factor-validation/external-payloads/compare 代理多引擎 payload 对比
    quant_ops_web 已展示 Alphalens / Qlib / vectorbt 标准 payload 对比矩阵
    quant_ops_web 已展示 comparison_report artifact reference
    quant_ops_api 已支持 artifact ledger preview / PostgreSQL 只读账本双路径
    quant_ops_api 已验证读取 101 真实 task/artifact 账本
    101 已只读确认 comparison_report.json 对象存在，并具备 factor_comparison_report.v1 metadata
    本地 quant_ops_api 已通过 SSH tunnel 只读联调 101 artifact，并返回 artifact_loaded
```

后续补强点是：为 Alphalens / Qlib / vectorbt 补第三方库执行层，把这些库的原始输出整理成 payload，再通过现有 adapter 进入 `FactorEvaluationResult` 和 `FactorComparisonReport`。

本阶段建议接入方式：

| 方向 | 推荐库 | 使用方式 |
| ---- | ---- | ---- |
| 股票截面验证 | Alphalens、Qlib | 已有 payload runner 边界；后续补第三方库执行层 |
| 股票资产定价因子 | OpenSourceAP/CrossSection | 参考因子定义和复现实验结构 |
| 期货时序量价 | vectorbt | 已有 payload runner 边界；Sharpe、回撤、换手等先进入审计 notes |
| 期货期限结构 | commodity-curve-factors | 参考 carry、slope、curvature、TSMOM / XSMOM 定义 |

规则评分先保持透明：

```text
final_score =
  rank_ic_ir_score
  + group_return_score
  + stability_score
  + turnover_penalty
  + coverage_score
  + drawdown_penalty
```

### 18.2 第二阶段：实验沉淀 + 审核记录 + 后验表现

目标：把研究实验、评分卡、研究员审核和上线后表现沉淀成可追溯数据，为第三阶段模型化打基础。

需要沉淀：

```text
ExperimentRun
EvaluationEngineResult
FactorScoreCard
ResearchReview
ForwardPerformance
MarketRegimeTag
DataQualitySnapshot
```

建议工具：

| 能力 | 推荐库 / 服务 | 使用方式 |
| ---- | ---- | ---- |
| 实验跟踪 | [MLflow](https://mlflow.org/) | 记录参数、指标、artifact、模型版本和研究实验 |
| 参数搜索 | [Optuna](https://optuna.org/) | 搜索 lookback、holding period、分组数、交易成本假设 |
| 漂移监控 | [Evidently](https://www.evidentlyai.com/) | 监控因子分布、覆盖率、数据质量和上线后衰减 |
| 生产审计 | PostgreSQL + MinIO | 保存 `task_runs`、`task_artifacts`、manifest 和报告产物 |

第二阶段仍不让模型自动决定生产准入。重点是让每次实验和审核都能复盘。

### 18.3 第三阶段：Meta Model / Ranking Model

目标：当历史实验、审核标签和后验表现足够多以后，再训练模型辅助判断因子质量。

模型输入可以包括：

```text
IC / Rank IC 序列特征
分组收益稳定性
多空收益和回撤
换手率和交易成本敏感性
覆盖率和缺失率
不同 market regime 下表现
不同 evaluation_engine 的结果差异
研究员审核标签
上线后 forward_performance
```

模型输出可以包括：

```text
factor_quality_score
candidate_pass_probability
expected_decay_risk
recommended_weight
review_priority
```

可选实现：

```text
Qlib model workflow
LightGBM / scikit-learn ranking model
MLflow model registry
Evidently drift report
```

强约束：

- Meta model 只能作为辅助判断，不能替代研究员审核。
- 训练标签必须来自已审计的历史实验、后验表现和审核结果。
- 模型输入必须来自标准协议，不允许直接读取各库的私有结果格式。
- 生产准入仍需要明确的 `review_decision`、`reviewer_notes`、`approved_by` 和审计记录。

### 18.4 其他扩展方向

基础闭环稳定后，再考虑以下能力：

```text
行业/市值中性化
barra 风格暴露
多因子组合优化
分钟级数据
盘口数据
新闻文本因子
公告文本因子
Hugging Face 文本 embedding
向量数据库
自动研究报告生成
任务调度系统
数据质量监控
实盘交易接口
```

特别说明：Hugging Face、向量数据库、文本 embedding 适合作为后续的另类数据/文本因子研究模块，不建议第一阶段进入主链路。当前优先级仍然是：

```text
行情数据稳定性 > 因子计算准确性 > 因子验证可靠性 > 回测真实性 > 模型复杂度
```

---

## 19. 项目命名建议

如果想更正式，可以使用以下英文名：

```text
quant_contracts
quant_data_hub
quant_factor_lab
quant_factor_validation
quant_model_lab
quant_backtest_engine
quant_risk_engine
quant_execution_gateway
quant_research_workspace
```

如果想更贴近公司内部平台，也可以命名为：

```text
zeta_quant_contracts
zeta_quant_data_hub
zeta_quant_factor_lab
zeta_quant_factor_validation
zeta_quant_model_lab
zeta_quant_backtest_engine
zeta_quant_risk_engine
zeta_quant_execution_gateway
zeta_quant_research_workspace
```

建议早期不要在项目名里加入太具体的策略名称，避免未来改方向时重命名困难。

---

## 20. 最终建议

当前最推荐的落地方式是：

```text
先建 quant_contracts
再建 quant_data_hub
然后建 quant_factor_lab
最后建 quant_factor_validation
```

先不要急着做：

```text
复杂机器学习
高频回测
实盘交易
向量数据库
Hugging Face 大模型文本分析
```

原因是这些都依赖一个前提：

```text
基础数据可信，因子计算可信，验证流程可信。
```

如果前三层不稳，后面的模型、回测、风控都会变成“看起来很复杂，但结果不一定可信”。

最好的第一阶段目标是：

```text
让任意一个新因子，从写代码到生成验证报告，有一条稳定、可复现、可审计的流水线。
```

这条流水线跑通后，后面再扩展模型、回测、风控和执行，会更稳。
