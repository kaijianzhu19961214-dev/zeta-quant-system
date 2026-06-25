# 行情数据流转方案

## 1. 当前结论

生产方案采用“原始行情稳定存储 + 因子独立管理 + 前复权批次缓存 + 分析库高速查询”的分层架构。

101 节点当前用于流程验证：

```text
共享盘 / Tushare
    ↓
PostgreSQL 控制面
    ↓
ClickHouse 行情分析库
    ↓
前复权缓存 / 后复权视图
    ↓
内部人员查询与回测
```

## 2. 系统职责

### PostgreSQL

定位：关系型控制面。

保存内容：

- 数据集定义
- 股票基础信息
- 交易日历
- 导入任务
- 复权因子表
- 前复权批次表
- 开发验证阶段的小规模行情表

不建议在 PostgreSQL 中长期保存 7T 级别分钟行情的全部派生缓存。

### MinIO

定位：对象存储和数据湖入口。

保存内容：

- 原始 zip/parquet
- 导入前后的中间 parquet
- 导入日志
- 月度前复权缓存产物
- 备份文件

### ClickHouse

定位：行情分析库和高速查询层。

保存内容：

- `market_data_1m_raw`
- `market_data_5m_raw`
- `market_data_1d_raw`
- `adjustment_factors`
- `qfq_batches`
- `market_data_1m_qfq_cache`
- `market_data_5m_qfq_cache`
- `market_data_1d_qfq_cache`
- 后复权查询视图

## 3. 数据口径

当前只处理：

- A 股股票
- `1d`
- `1m`
- `5m`

当前不处理：

- 指数
- ETF
- 可转债
- 秒级数据
- tick 数据

## 4. 主行情数据

主行情表保存稳定字段：

```text
dataset_code
code
trade_time / date
open
high
low
close
pre_close
change
pct_chg
vol
amount
adj_factor
hfq_factor
source_name
created_at
```

缺少复权因子时：

```text
adj_factor = 1
hfq_factor = 1
```

这样可以保证记录完整入库，同时通过导入统计中的 `default_factor_count` 审计缺因子的数量。

## 5. 后复权

后复权不依赖未来基准日。

公式：

```text
hfq_price = raw_price * hfq_factor
hfq_factor = adj_factor
```

生产建议：

- 后复权可以通过 ClickHouse 视图动态计算。
- 如果内部查询非常频繁，也可以物化保存 `hfq_*`。
- 不需要按月重算历史后复权字段。

## 6. 前复权

前复权依赖基准日。

公式：

```text
qfq_factor = current_adj_factor / base_adj_factor
qfq_price = raw_price * qfq_factor
```

业务口径：

- 每月做一次回撤或回测计算。
- 每月确定一个 `qfq_base_date`。
- 每月生成一个 `batch_id`。
- 生成对应批次的 `qfq_cache`。

示例：

```text
batch_id = qfq_202604
qfq_base_date = 2026-04-30
```

查询前复权时查缓存表：

```sql
SELECT code, trade_time, qfq_close
FROM quant_market.market_data_1m_qfq_cache
WHERE batch_id = 'qfq_202604'
  AND dataset_code = 'a_share_1m'
  AND code = '000001.SZ'
ORDER BY trade_time;
```

## 7. 为什么不重写主表 qfq 字段

不建议每月 `UPDATE market_data_1m SET qfq_* = ...`。

原因：

- 超大表 UPDATE 会产生大量 WAL。
- 会造成 PostgreSQL 表膨胀。
- 会触发大量 vacuum 和索引维护。
- HDD 阵列随机写压力大。
- 重算期间查询性能容易波动。

因此生产方案采用：

```text
主表稳定保存原始价和因子
前复权按月生成缓存表
查询前复权走缓存表
```

## 8. 101 验证链路

在 101 上验证：

```text
1. PostgreSQL 保留当前控制面和开发验证表
2. MinIO 保留现有对象存储服务
3. Docker 部署 ClickHouse 单节点
4. 用少量交易日数据导入 ClickHouse raw 表
5. 生成一个 qfq batch
6. 对比 PostgreSQL 与 ClickHouse 查询结果
7. 让内部人员测试典型查询 SQL
```

验证脚本：

```bash
# PostgreSQL 当前样本数据 -> ClickHouse raw 表
python scripts/sync_pg_to_clickhouse.py --timeframe all --chunk-size 20000

# 共享盘 parquet/zip -> ClickHouse raw 表
python scripts/import_shared_market_data_to_clickhouse.py \
  --shared-root /Volumes/nfs/data/A股分钟数据 \
  --timeframe all \
  --date 20260313 \
  --replace-day
```

如果在 101 节点直接读取共享盘，需要先挂载 NFS。Mac 当前挂载源为：

```text
192.168.2.128:/fs/1000/nfs
```

101 节点建议挂载到 `/mnt/nfs`：

```bash
sudo apt install -y nfs-common
sudo mkdir -p /mnt/nfs
sudo mount -t nfs 192.168.2.128:/fs/1000/nfs /mnt/nfs
```

挂载后 101 上的共享盘路径应为：

```text
/mnt/nfs/data/A股分钟数据
```

对应导入命令：

```bash
python scripts/import_shared_market_data_to_clickhouse.py \
  --shared-root /mnt/nfs/data/A股分钟数据 \
  --timeframe all \
  --date 20260313 \
  --replace-day
```

共享盘直写脚本会写入：

- `adjustment_factors`
- `market_data_1d_raw`
- `market_data_1m_raw`
- `market_data_5m_raw`

缺失复权因子时使用 `1`，并在输出摘要中记录 `default_factor_count`。

前复权缓存生成脚本：

```bash
python scripts/build_clickhouse_qfq_cache.py --timeframe all --replace
```

默认行为：

- 基准日取 `market_data_1d_raw` 中最新交易日。
- 批次号默认为 `qfq_YYYYMMDD`。
- 前复权因子为 `raw.hfq_factor / base.hfq_factor`。
- 缺少基准日因子或基准日因子为 `0` 时使用 `1`。
- 写入 `market_data_1d_qfq_cache`、`market_data_1m_qfq_cache`、`market_data_5m_qfq_cache`。

内部查询示例见：

```text
docs/clickhouse_query_examples.md
```

SDK / API 设计和 Codex 提示词模板见：

```text
docs/sdk_api_design.md
```

## 9. Tushare 全市场日线验证链路

开发验证阶段先把日线跑完整，分钟线后续再迁移。

当前 101 节点已验证：

- Tushare 可按交易日拉取全市场 A 股日线。
- `2026-06-01` 至 `2026-06-10` 共 8 个开市日已写入 ClickHouse。
- `market_data_1d_raw` 保存原始价和 `adj_factor/hfq_factor`。
- `v_market_data_1d_hfq` 提供后复权视图。
- `market_data_1d_qfq_cache` 已生成 `qfq_20260610` 前复权批次。

导入命令：

```bash
python scripts/import_tushare_market_data_to_clickhouse.py \
  --all-a-shares \
  --timeframe 1d \
  --start-date 20260601 \
  --end-date 20260610 \
  --replace \
  --chunk-size 10000
```

生成日线前复权缓存：

```bash
python scripts/build_clickhouse_qfq_cache.py \
  --timeframe 1d \
  --base-date 20260610 \
  --batch-id qfq_20260610 \
  --start-date 20260601 \
  --end-date 20260610 \
  --replace
```

101 节点测试页面：

```text
http://192.168.2.101:8000/node-tests
```

该页面会展示服务状态、ClickHouse 日线覆盖、最新交易日 raw/hfq/qfq 样例。

## 10. 生产链路

生产导入建议：

```text
共享盘 / 原始数据包
    ↓
归档到 MinIO
    ↓
批量解析 parquet
    ↓
写入 ClickHouse raw 表
    ↓
写入 PostgreSQL 导入任务状态
    ↓
按月生成 qfq_cache
    ↓
内部查询 / 回测
```

PostgreSQL 继续保存任务和元数据；ClickHouse 承担大规模行情查询。

## 11. 参考

- ClickHouse Docker: https://clickhouse.com/docs/install/docker
- ClickHouse MergeTree: https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree
- ClickHouse S3/MinIO 集成: https://clickhouse.com/docs/integrations/s3
- ClickHouse 分区建议: https://clickhouse.com/docs/engines/table-engines/mergetree-family/custom-partitioning-key
