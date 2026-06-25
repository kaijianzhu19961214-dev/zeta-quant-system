# quant-data-ingestion-layer 数据库结构说明

## 1. 设计目标

数据库用于存储第三方购买的 A 股行情数据，并为内部人员、Codex、DBeaver 和后续计算流程提供统一查询入口。

当前开发阶段只处理：

- A 股日线数据
- A 股 1 分钟行情数据
- 股票基础信息
- 交易日历
- 导入任务记录
- 价格复权因子与复权后价格

暂不处理：

- 秒级数据
- Tick / Level2 数据
- 实时数据推送
- 因子计算
- 回测结果

## 2. 数据来源

共享盘路径：

```text
/Volumes/nfs/data/A股分钟数据
```

已识别的数据文件：

```text
1m_price_zip/YYYY.zip
5m_price_zip/YYYY.zip
1d_price.zip
4.21更新/A股分钟数据/A股日线/stock_basic.parquet
4.21更新/A股分钟数据/A股日线/calendar.parquet
```

当前优先入库：

```text
stock_basic.parquet
calendar.parquet
1d_price.zip
1m_price_zip/YYYY.zip
```

复权因子来源：

```text
1d_price 中已有 adj_factor
分钟线需要通过外部 Tushare 代理接口补充对应 code/date 的 adj_factor
```

Tushare 代理接口作为补充数据源，主要用于获取复权因子和后续补数。接口 token 通过 `.env` 配置，不写入代码和文档明文。

## 3. 数据库表清单

```text
datasets
securities
trading_calendar
ingestion_jobs
market_data_1d
market_data_1m
staging_market_data_1m
alembic_version
```

## 4. 表关系概览

```text
datasets.dataset_code
    ↓
market_data_1d.dataset_code
market_data_1m.dataset_code
ingestion_jobs.dataset_code

securities.code
    ↓
market_data_1d.code
market_data_1m.code

trading_calendar.date
    ↓
market_data_1d.date
market_data_1m.date
```

字段命名原则：

- 数据字段尽量与共享盘 parquet/csv 原始字段名保持一致，方便内部人员直接查询。
- 系统补充字段使用项目统一命名，例如 `dataset_code`、`source_name`、`created_at`。
- 行情表使用 `code`，不再将源字段 `code` 改名为 `symbol`。
- 行情表使用 `date`，不再将源字段 `date` 改名为 `trade_date`。
- 行情表保留 `open`、`high`、`low`、`close`、`vol` 等源字段名。
- 行情表中的源字段 `open`、`high`、`low`、`close`、`pre_close`、`change`、`vwap` 存储原始价格。
- 行情表中的 `qfq_*` 字段存储前复权价格。
- 行情表中的 `hfq_*` 字段存储后复权价格。
- 每条行情记录保留 `qfq_factor` 和 `hfq_factor`，用于追溯和动态复权。
- 每条行情记录保留 `qfq_base_date`，用于标记当前 `qfq_*` 字段采用的前复权基准日。

价格复权原则：

- `open`、`high`、`low`、`close`、`pre_close`、`change`、`vwap` 保持共享盘或 Tushare `daily` 原始价格口径。
- `qfq_factor` 记录前复权乘数。
- `hfq_factor` 记录后复权乘数。
- `qfq_base_date` 记录前复权基准日；当前按月度回撤计算批次确定，预计每月重算一次。
- `adj_factor` 为兼容字段，等价于共享盘或 Tushare 返回的原始复权因子，当前可视作 `hfq_factor` 的来源值。
- `pct_chg` 不需要复权，保持源数据口径。
- `vol` 为原始成交量，不做复权。
- `amount` 为原始成交额，不做复权。
- 分钟线源文件没有 `adj_factor`，导入时需要按 `code + date` 关联日线或 Tushare 因子表。

当前同时保存三套价格口径：

```text
raw_price = source_price
qfq_price = raw_price * qfq_factor
hfq_price = raw_price * hfq_factor
```

API 导入行为：

- 请求中的价格字段必须是原始价格。
- 服务端保留原始价格，并基于 `qfq_factor`、`hfq_factor` 生成前复权和后复权字段。
- 当某条记录缺少 `qfq_factor` 或 `hfq_factor` 时，默认使用 `1`，即复权价格等于原始价格。
- `qfq_base_date` 未传入时默认使用该记录的 `date`。

Tushare 代理 token 通过 `.env` 的 `TUSHARE_TOKEN` 配置，禁止写入代码、提交到仓库或出现在文档明文中。

前后复权验证过程和完整导入规则见 `docs/price_adjustment_logic.md`。

当前开发和生产阶段原则上不使用数据库外键，原因：

- 大批量 COPY 导入时外键会增加写入成本
- 历史数据量大，导入阶段优先保证吞吐
- 内部查询性能优先，避免外键维护成本影响导入和更新
- 通过导入前校验和导入后审计保证数据一致性

数据一致性通过以下方式保证：

- 导入前校验 `code` 是否存在于 `securities`
- 导入前校验 `date` 是否存在于 `trading_calendar`
- 导入任务记录 `ingestion_jobs`
- 导入后抽样审计
- 离线一致性检查 SQL

除非后续明确要求，否则不在行情大表上增加外键约束。

## 5. 数据维护与唯一性策略

历史数据采用“一次性批量导入 + 后续按交易日增量补导”的维护方式。

唯一性约束：

```text
market_data_1d: PK(dataset_code, code, date)
market_data_1m: PK(dataset_code, code, trade_time)
market_data_5m: PK(dataset_code, code, trade_time)
```

含义：

- `dataset_code` 区分数据来源和频率，例如 `a_share_1m`、`a_share_5m`、`a_share_1d`。
- `code` 区分证券。
- `date` 或 `trade_time` 区分交易日期或分钟时间。
- 重复导入同一交易日时，正式表使用唯一键防止重复记录。

导入建议：

- 生产历史数据导入优先使用 `COPY -> staging 表 -> 校验/去重 -> 正式分区表`。
- API 批量写入适合开发验证、小批量补导和接口联调。
- 每个交易日导入后记录 `source_rows`、`inserted_count`、`skipped_count`、`default_factor_count`。
- 对缺少复权因子的记录按因子 `1` 入库，并通过 `default_factor_count` 审计数量。
- 历史 3T 数据不建议反复全量重导，除非数据口径发生重大变化。

数据范围：

- 当前只保留 A 股股票数据。
- 当前只保留 `1d`、`1m`、`5m` 三类频率。
- 当前不导入指数、ETF、可转债等非股票数据。

## 6. datasets

用途：记录数据集元信息。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | 自增主键 |
| dataset_code | varchar(64) | unique, not null | 数据集编码 |
| dataset_name | varchar(128) | not null | 数据集名称 |
| source_name | varchar(128) | not null | 数据来源 |
| description | text | nullable | 描述 |
| is_active | boolean | not null, default true | 是否启用 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |

索引：

```text
PK(id)
UNIQUE(dataset_code)
INDEX(dataset_code)
```

建议初始数据集编码：

```text
a_share_1d
a_share_1m
```

## 6. securities

用途：股票基础信息，来源于 `stock_basic.parquet`。

| 字段 | 类型 | 约束 | 来源字段 | 说明 |
|---|---|---|---|---|
| code | varchar(32) | PK | code | 证券代码，如 000001.SZ |
| symbol | varchar(16) | not null | symbol | 纯数字代码 |
| name | varchar(128) | not null | name | 股票名称 |
| area | varchar(64) | nullable | area | 地区 |
| industry | varchar(128) | nullable | industry | 行业 |
| fullname | varchar(256) | not null | fullname | 公司全称 |
| enname | varchar(256) | not null | enname | 英文名 |
| cnspell | varchar(64) | not null | cnspell | 拼音缩写 |
| market | varchar(64) | not null | market | 市场板块 |
| exchange | varchar(16) | not null | exchange | 交易所 |
| curr_type | varchar(16) | not null | curr_type | 币种 |
| list_status | varchar(8) | not null | list_status | 上市状态 |
| list_date | date | not null | list_date | 上市日期 |
| delist_date | date | nullable | delist_date | 退市日期 |
| is_hs | varchar(8) | not null | is_hs | 是否沪深港通 |
| act_name | varchar(256) | nullable | act_name | 实控人 |
| act_ent_type | varchar(64) | nullable | act_ent_type | 实控人类型 |
| created_at | timestamptz | not null | generated | 创建时间 |
| updated_at | timestamptz | not null | generated | 更新时间 |

索引：

```text
PK(code)
INDEX(symbol)
INDEX(name)
INDEX(industry)
INDEX(exchange)
INDEX(list_status)
```

说明：

- `code` 使用带交易所后缀的代码作为主键，例如 `000001.SZ`。
- 行情表中的 `code` 与本表 `code` 保持一致。

## 7. trading_calendar

用途：交易日历，来源于 `calendar.parquet`。

| 字段 | 类型 | 约束 | 来源字段 | 说明 |
|---|---|---|---|---|
| date | date | PK | date | 交易日期 |
| created_at | timestamptz | not null | generated | 创建时间 |
| updated_at | timestamptz | not null | generated | 更新时间 |

索引：

```text
PK(date)
```

## 8. market_data_1m

用途：A 股 1 分钟行情正式表，来源于 `1m_price_zip/YYYY.zip` 中的每日 parquet。

分区：

```text
PARTITION BY RANGE (trade_time)
```

建议分区粒度：

```text
按月分区
```

| 字段 | 类型 | 约束 | 来源字段 | 说明 |
|---|---|---|---|---|
| dataset_code | varchar(64) | PK part | generated | 数据集编码 |
| code | varchar(32) | PK part | code | 证券代码 |
| trade_time | timestamptz | PK part | trade_time | 分钟时间 |
| date | date | not null | date | 交易日期 |
| open | numeric(20,6) | nullable | open | 开盘价 |
| high | numeric(20,6) | nullable | high | 最高价 |
| low | numeric(20,6) | nullable | low | 最低价 |
| close | numeric(20,6) | nullable | close | 收盘价 |
| pre_close | numeric(20,6) | nullable | pre_close | 前收盘价 |
| change | numeric(20,6) | nullable | change | 涨跌额 |
| pct_chg | numeric(20,6) | nullable | pct_chg | 涨跌幅 |
| vol | bigint | nullable | vol | 成交量 |
| amount | numeric(24,6) | nullable | amount | 成交额 |
| adj_factor | numeric(20,6) | nullable | external | 兼容复权因子 |
| qfq_factor | numeric(24,10) | nullable | external | 前复权乘数 |
| hfq_factor | numeric(24,10) | nullable | external | 后复权乘数 |
| qfq_base_date | date | nullable | generated | 前复权基准日 |
| qfq_open/qfq_high/qfq_low/qfq_close | numeric(20,6) | nullable | generated | 前复权 OHLC |
| qfq_pre_close/qfq_change | numeric(20,6) | nullable | generated | 前复权前收盘价和涨跌额 |
| hfq_open/hfq_high/hfq_low/hfq_close | numeric(20,6) | nullable | generated | 后复权 OHLC |
| hfq_pre_close/hfq_change | numeric(20,6) | nullable | generated | 后复权前收盘价和涨跌额 |
| source_name | varchar(128) | not null | generated | 数据来源 |
| raw_payload | jsonb | nullable | raw row | 原始字段快照，可选 |
| created_at | timestamptz | not null | generated | 入库时间 |

索引：

```text
PK(dataset_code, code, trade_time)
INDEX(dataset_code, trade_time)
INDEX(dataset_code, date, code)
```

典型查询：

```sql
SELECT *
FROM market_data_1m
WHERE dataset_code = 'a_share_1m'
  AND code = '000001.SZ'
  AND trade_time >= '2026-01-01 00:00:00+08'
  AND trade_time < '2026-02-01 00:00:00+08'
ORDER BY trade_time;
```

按交易日查询全市场或一批股票：

```sql
SELECT *
FROM market_data_1m
WHERE dataset_code = 'a_share_1m'
  AND date = '2026-03-13'
  AND code IN ('000001.SZ', '000002.SZ')
ORDER BY code, trade_time;
```

索引说明：

- `PK(dataset_code, code, trade_time)` 支持单只股票历史区间查询和防重复写入。
- `INDEX(dataset_code, trade_time)` 支持按时间段扫描全市场分钟数据。
- `INDEX(dataset_code, date, code)` 支持按交易日查询全市场或一批股票。

## 9. staging_market_data_1m

用途：A 股 1 分钟行情导入中间表。

导入流程：

```text
parquet 文件
    ↓
标准化字段
    ↓
COPY 到 staging_market_data_1m
    ↓
去重 / 校验
    ↓
写入 market_data_1m
```

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | 自增主键 |
| job_id | varchar(64) | not null | 导入任务 ID |
| dataset_code | varchar(64) | not null | 数据集编码 |
| code | varchar(32) | not null | 证券代码 |
| trade_time | timestamptz | not null | 分钟时间 |
| date | date | not null | 交易日期 |
| open | numeric(20,6) | nullable | 开盘价 |
| high | numeric(20,6) | nullable | 最高价 |
| low | numeric(20,6) | nullable | 最低价 |
| close | numeric(20,6) | nullable | 收盘价 |
| pre_close | numeric(20,6) | nullable | 前收盘价 |
| change | numeric(20,6) | nullable | 涨跌额 |
| pct_chg | numeric(20,6) | nullable | 涨跌幅 |
| vol | bigint | nullable | 成交量 |
| amount | numeric(24,6) | nullable | 成交额 |
| adj_factor | numeric(20,6) | nullable | 兼容复权因子 |
| qfq_factor | numeric(24,10) | nullable | 前复权乘数 |
| hfq_factor | numeric(24,10) | nullable | 后复权乘数 |
| qfq_base_date | date | nullable | 前复权基准日 |
| qfq_open/qfq_high/qfq_low/qfq_close | numeric(20,6) | nullable | 前复权 OHLC |
| qfq_pre_close/qfq_change | numeric(20,6) | nullable | 前复权前收盘价和涨跌额 |
| hfq_open/hfq_high/hfq_low/hfq_close | numeric(20,6) | nullable | 后复权 OHLC |
| hfq_pre_close/hfq_change | numeric(20,6) | nullable | 后复权前收盘价和涨跌额 |
| source_name | varchar(128) | not null | 数据来源 |
| raw_payload | jsonb | nullable | 原始字段快照 |
| created_at | timestamptz | not null | 入库时间 |

索引：

```text
PK(id)
INDEX(job_id)
INDEX(dataset_code, code, trade_time)
```

## 10. market_data_5m

用途：A 股 5 分钟行情正式表，来源于 `5m_price_zip/YYYY.zip`。

分区：

```text
PARTITION BY RANGE (trade_time)
```

建议分区粒度：

```text
按月分区
```

字段与 `market_data_1m` 保持一致：

| 字段 | 类型 | 约束 | 来源字段 | 说明 |
|---|---|---|---|---|
| dataset_code | varchar(64) | PK part | generated | 数据集编码 |
| code | varchar(32) | PK part | code | 证券代码 |
| trade_time | timestamptz | PK part | trade_time | 5 分钟时间 |
| date | date | not null | date | 交易日期 |
| open | numeric(20,6) | nullable | open | 原始开盘价 |
| high | numeric(20,6) | nullable | high | 原始最高价 |
| low | numeric(20,6) | nullable | low | 原始最低价 |
| close | numeric(20,6) | nullable | close | 原始收盘价 |
| pre_close | numeric(20,6) | nullable | pre_close | 原始前收盘价 |
| change | numeric(20,6) | nullable | change | 原始涨跌额 |
| pct_chg | numeric(20,6) | nullable | pct_chg | 涨跌幅 |
| vol | bigint | nullable | vol | 原始成交量 |
| amount | numeric(24,6) | nullable | amount | 原始成交额 |
| adj_factor | numeric(20,6) | nullable | external | 兼容复权因子 |
| qfq_factor | numeric(24,10) | nullable | external | 前复权乘数 |
| hfq_factor | numeric(24,10) | nullable | external | 后复权乘数 |
| qfq_base_date | date | nullable | generated | 前复权基准日 |
| qfq_open/qfq_high/qfq_low/qfq_close | numeric(20,6) | nullable | generated | 前复权 OHLC |
| qfq_pre_close/qfq_change | numeric(20,6) | nullable | generated | 前复权前收盘价和涨跌额 |
| hfq_open/hfq_high/hfq_low/hfq_close | numeric(20,6) | nullable | generated | 后复权 OHLC |
| hfq_pre_close/hfq_change | numeric(20,6) | nullable | generated | 后复权前收盘价和涨跌额 |
| source_name | varchar(128) | not null | generated | 数据来源 |
| raw_payload | jsonb | nullable | raw row | 原始字段快照，可选 |
| created_at | timestamptz | not null | generated | 入库时间 |

索引：

```text
PK(dataset_code, code, trade_time)
INDEX(dataset_code, trade_time)
INDEX(dataset_code, date, code)
```

索引说明与 `market_data_1m` 一致。

## 11. staging_market_data_5m

用途：A 股 5 分钟行情导入中间表。

字段与 `staging_market_data_1m` 保持一致。

索引：

```text
PK(id)
INDEX(job_id)
INDEX(dataset_code, code, trade_time)
```

## 12. market_data_1d

用途：A 股日线行情正式表，来源于 `1d_price.zip` 或新版目录中的日线 zip。

分区：

```text
PARTITION BY RANGE (date)
```

建议分区粒度：

```text
按年或按月分区
```

| 字段 | 类型 | 约束 | 来源字段 | 说明 |
|---|---|---|---|---|
| dataset_code | varchar(64) | PK part | generated | 数据集编码 |
| code | varchar(32) | PK part | code | 证券代码 |
| date | date | PK part | date | 交易日期 |
| open | numeric(20,6) | nullable | open | 开盘价 |
| high | numeric(20,6) | nullable | high | 最高价 |
| low | numeric(20,6) | nullable | low | 最低价 |
| close | numeric(20,6) | nullable | close | 收盘价 |
| pre_close | numeric(20,6) | nullable | pre_close | 前收盘价 |
| change | numeric(20,6) | nullable | change | 涨跌额 |
| pct_chg | numeric(20,6) | nullable | pct_chg | 涨跌幅 |
| vol | bigint | nullable | vol | 成交量 |
| amount | numeric(24,6) | nullable | amount | 成交额 |
| adj_factor | numeric(20,6) | nullable | adj_factor | 兼容复权因子 |
| qfq_factor | numeric(24,10) | nullable | generated | 前复权乘数 |
| hfq_factor | numeric(24,10) | nullable | adj_factor | 后复权乘数 |
| qfq_base_date | date | nullable | generated | 前复权基准日 |
| vwap | numeric(20,6) | nullable | vwap | 原始成交均价 |
| qfq_vwap | numeric(20,6) | nullable | generated | 前复权成交均价 |
| hfq_vwap | numeric(20,6) | nullable | generated | 后复权成交均价 |
| source_name | varchar(128) | not null | generated | 数据来源 |
| raw_payload | jsonb | nullable | raw row | 原始字段快照 |
| created_at | timestamptz | not null | generated | 入库时间 |

索引：

```text
PK(dataset_code, code, date)
INDEX(dataset_code, date)
```

## 13. ingestion_jobs

用途：记录每次文件导入任务。

定位说明：

- `ingestion_jobs` 已存在，适合记录行情导入、补导、重导这类数据接入任务。
- 它不是完整量化流程的唯一任务表。
- 后续 API / SDK 化后，建议新增更通用的 `task_runs` 和 `task_artifacts`，用于记录前复权批次生成、因子计算、回测、研究产物上传等任务。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | integer | PK | 自增主键 |
| job_id | uuid | unique, not null | 任务 UUID |
| dataset_code | varchar(64) | not null | 数据集编码 |
| source_name | varchar(128) | not null | 数据来源 |
| file_path | text | nullable | 文件路径 |
| received_count | integer | not null, default 0 | 接收行数 |
| inserted_count | integer | not null, default 0 | 写入行数 |
| skipped_count | integer | not null, default 0 | 跳过行数 |
| failed_count | integer | not null, default 0 | 失败行数 |
| status | varchar(32) | not null | 任务状态 |
| error_message | text | nullable | 错误信息 |
| started_at | timestamptz | not null | 开始时间 |
| finished_at | timestamptz | nullable | 结束时间 |

状态建议：

```text
pending
running
succeeded
failed
partial_failed
```

索引：

```text
PK(id)
UNIQUE(job_id)
INDEX(job_id)
INDEX(dataset_code)
INDEX(status)
```

## 13.1 task_runs，已落地表

用途：记录通用任务运行实例，覆盖导入、前复权缓存生成、因子计算、回测、研究员上传产物等流程。

当前状态：已通过 Alembic `0011_task_runs` 创建。

当前 API / SDK 已接入该表；研究员侧只通过 SDK 创建或查询任务。
账号、token、数据库密码、MinIO 密钥均通过环境变量或服务端配置管理，不写入任务参数。

建议字段：

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | PK | 自增主键 |
| task_id | uuid | unique, not null | 任务 UUID |
| task_type | varchar(64) | not null | 任务类型 |
| task_name | varchar(256) | not null | 任务名称 |
| owner | varchar(128) | nullable | 发起人或系统账号 |
| status | varchar(32) | not null | 任务状态 |
| input_params | jsonb | nullable | 输入参数 |
| output_summary | jsonb | nullable | 输出摘要 |
| error_message | text | nullable | 错误信息 |
| description | text | nullable | 任务说明 |
| created_at | timestamptz | not null | 创建时间 |
| updated_at | timestamptz | not null | 更新时间 |
| started_at | timestamptz | nullable | 开始时间 |
| finished_at | timestamptz | nullable | 结束时间 |

任务类型建议：

```text
factor_compute
backtest
research_export
data_sample
```

状态建议：

```text
created
running
succeeded
failed
cancelled
```

示例：

```json
{
  "task_id": "0d6a6e89-0f6f-4d91-9179-8f65e4fb0a11",
  "task_type": "backtest",
  "status": "succeeded",
  "input_params": {
    "codes": ["600527.SH"],
    "timeframe": "1m",
    "price_mode": "qfq",
    "batch_id": "qfq_20260313"
  },
  "output_summary": {
    "annual_return": 0.12,
    "max_drawdown": -0.08,
    "artifact_count": 2
  }
}
```

索引：

```text
PK(id)
UNIQUE(task_id)
INDEX(task_id)
INDEX(status)
INDEX(task_type, status, created_at)
INDEX(owner, created_at)
```

## 13.2 task_artifacts，已落地表

用途：记录任务产生或使用的文件产物，例如 MinIO 上的 parquet、回测报告、因子文件、失败样本等。

当前状态：已通过 Alembic `0011_task_runs` 创建。

说明：该表不使用数据库外键，只通过 `task_id` 建索引关联 `task_runs.task_id`。
这样可以避免高频产物登记和批量查询时被外键约束检查放大写入成本。

建议字段：

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| id | bigint | PK | 自增主键 |
| artifact_id | uuid | unique, not null | 产物 UUID |
| task_id | uuid | index | 关联 `task_runs.task_id` |
| artifact_type | varchar(64) | not null | 产物类型 |
| storage_type | varchar(32) | not null | `minio`、`nfs`、`local` |
| uri | text | not null | 文件 URI 或路径 |
| bucket_name | varchar(128) | not null | MinIO bucket |
| object_key | text | not null | MinIO object key |
| file_size_bytes | bigint | nullable | 文件大小 |
| etag | varchar(128) | nullable | MinIO etag |
| content_type | varchar(128) | nullable | 文件类型 |
| artifact_name | varchar(256) | nullable | 产物名称 |
| metadata | jsonb | nullable | 产物元数据 |
| created_at | timestamptz | not null | 创建时间 |

产物类型建议：

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

示例：

```json
{
  "artifact_type": "backtest_trades",
  "storage_type": "minio",
  "bucket_name": "quant-factor-data",
  "object_key": "backtests/momentum_v1/run_20260618/trades.parquet",
  "uri": "s3://quant-factor-data/backtests/momentum_v1/run_20260618/trades.parquet"
}
```

索引：

```text
PK(id)
UNIQUE(artifact_id)
INDEX(task_id)
INDEX(artifact_type, created_at)
INDEX(bucket_name, object_key)
```

## 14. adjustment_factors

用途：保存独立复权因子，供后复权计算和前复权批次生成使用。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| dataset_code | varchar(64) | PK part | 数据集编码，例如 `a_share_adj_factor` |
| code | varchar(32) | PK part | 证券代码 |
| date | date | PK part | 交易日期 |
| adj_factor | numeric(24,10) | not null | 复权因子；缺失时默认按 `1` 处理 |
| source_name | varchar(128) | not null | 数据来源 |
| raw_payload | jsonb | nullable | 原始字段快照 |
| created_at | timestamptz | not null | 入库时间 |

索引：

```text
PK(dataset_code, code, date)
INDEX(dataset_code, date)
INDEX(code, date)
```

## 15. qfq_batches

用途：记录前复权缓存批次。

| 字段 | 类型 | 约束 | 说明 |
|---|---|---|---|
| batch_id | varchar(64) | PK | 批次 ID，例如 `qfq_202604` |
| qfq_base_date | date | not null | 本批次前复权基准日 |
| status | varchar(32) | not null | 批次状态 |
| description | text | nullable | 批次说明 |
| raw_payload | jsonb | nullable | 批次参数 |
| created_at | timestamptz | not null | 创建时间 |
| finished_at | timestamptz | nullable | 完成时间 |

状态建议：

```text
pending
running
succeeded
failed
```

## 16. ClickHouse 行情分析表

ClickHouse 表定义位于：

```text
deploy/clickhouse/initdb/001_market_data.sql
```

主要表：

```text
quant_market.market_data_1m_raw
quant_market.market_data_5m_raw
quant_market.market_data_1d_raw
quant_market.adjustment_factors
quant_market.qfq_batches
quant_market.market_data_1m_qfq_cache
quant_market.market_data_5m_qfq_cache
quant_market.market_data_1d_qfq_cache
quant_market.v_market_data_1m_hfq
quant_market.v_market_data_5m_hfq
quant_market.v_market_data_1d_hfq
```

主行情表保存原始价和稳定因子；前复权结果按 `batch_id + qfq_base_date` 写入缓存表。
后复权结果通过 `v_market_data_*_hfq` 视图动态计算，避免重写 raw 表。

## 17. 字段命名映射

分钟线和日线字段映射：

| 源字段 | 入库字段 |
|---|---|
| code | code |
| trade_time | trade_time |
| date | date |
| open | open |
| high | high |
| low | low |
| close | close |
| pre_close | pre_close |
| change | change |
| pct_chg | pct_chg |
| vol | vol |
| amount | amount |
| adj_factor | adj_factor |
| qfq_factor | generated |
| hfq_factor | adj_factor |
| qfq_base_date | generated |
| qfq_* | generated |
| hfq_* | generated |
| vwap | vwap |

价格字段入库规则：

| 源字段 | 入库规则 |
|---|---|
| open | 原样写入 open，同时生成 qfq_open、hfq_open |
| high | 原样写入 high，同时生成 qfq_high、hfq_high |
| low | 原样写入 low，同时生成 qfq_low、hfq_low |
| close | 原样写入 close，同时生成 qfq_close、hfq_close |
| pre_close | 原样写入 pre_close，同时生成 qfq_pre_close、hfq_pre_close |
| change | 原样写入 change，同时生成 qfq_change、hfq_change |
| vwap | 原样写入 vwap，同时生成 qfq_vwap、hfq_vwap |
| pct_chg | 保持原值 |
| vol | 保持原值 |
| amount | 保持原值 |

## 18. 生产口径说明

当前 PostgreSQL 行情表中仍保留 `qfq_*` 字段，主要用于 101 开发验证和历史兼容。

生产导入 7T 数据前，建议调整为：

```text
PostgreSQL:
  元数据、任务、因子、批次

ClickHouse raw 表:
  原始价 + adj_factor / hfq_factor

ClickHouse qfq_cache 表:
  按月度 batch_id 保存前复权缓存
```

生产不建议每月对 PostgreSQL 或 ClickHouse 主行情 raw 表做全量 `UPDATE qfq_*`。

## 19. 当前 Alembic 版本

当前开发库迁移版本：

```text
0010_factor_batches
```
