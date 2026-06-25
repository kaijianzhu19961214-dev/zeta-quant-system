# 前后复权与三价格口径技术逻辑

## 1. 目标

行情表同时保存三套价格：

- 原始价格
- 前复权价格
- 后复权价格

内部人员可以直接查询固定口径价格，也可以基于原始价格和因子做动态复权处理。

适用表：

- `market_data_1m`
- `market_data_5m`
- `market_data_1d`
- 对应 staging 表

## 2. 字段口径

原始价格字段保持共享盘字段名：

- `open`
- `high`
- `low`
- `close`
- `pre_close`
- `change`
- `vwap`，当前仅日线有该字段

前复权价格字段加 `qfq_` 前缀：

- `qfq_open`
- `qfq_high`
- `qfq_low`
- `qfq_close`
- `qfq_pre_close`
- `qfq_change`
- `qfq_vwap`，当前仅日线有该字段

后复权价格字段加 `hfq_` 前缀：

- `hfq_open`
- `hfq_high`
- `hfq_low`
- `hfq_close`
- `hfq_pre_close`
- `hfq_change`
- `hfq_vwap`，当前仅日线有该字段

因子字段：

- `qfq_factor`：前复权乘数
- `hfq_factor`：后复权乘数
- `qfq_base_date`：前复权基准日
- `adj_factor`：兼容字段，等价于共享盘或 Tushare 返回的原始复权因子，当前可视作 `hfq_factor` 的来源值

## 3. 计算公式

入库前，先确认原始价格字段没有复权。

后复权：

```text
hfq_price = raw_price * hfq_factor
```

前复权：

```text
qfq_price = raw_price * qfq_factor
```

当前 `qfq_factor` 的推荐生成方式：

```text
qfq_factor = adj_factor / latest_adj_factor
```

其中 `latest_adj_factor` 为同一证券在 `qfq_base_date` 上的复权因子。

当前业务口径：

- 预计每月做一次回撤计算。
- 前复权基准日按月度计算批次确定。
- 每月重算时，不重写 raw 大表，生成新的 `qfq_cache` 批次。
- 每条缓存记录通过 `batch_id` 和 `qfq_base_date` 标记使用的前复权基准日。
- PostgreSQL 开发表里的 `qfq_factor` 和 `qfq_*` 字段仅用于验证和历史兼容。
- 当前 ClickHouse 验证环境使用 `scripts/build_clickhouse_qfq_cache.py` 生成 `qfq_cache`。

当前 `hfq_factor` 的推荐生成方式：

```text
hfq_factor = adj_factor
```

缺少复权因子时：

```text
qfq_factor = 1
hfq_factor = 1
adj_factor = 1
```

此时复权价格等于原始价格，并通过导入统计中的 `default_factor_count` 审计数量。

## 4. 共享盘与 Tushare 校验

共享盘日线源文件包含原始价格和 `adj_factor`。

以 `000651.SZ` 在 `2026-01-05` 为例：

```text
共享盘 close = 40.76
共享盘 adj_factor = 224.7531
Tushare daily close = 40.76
Tushare adj_factor = 224.7531
```

由此可判断共享盘 `open/high/low/close/pre_close/change/vwap` 是原始价格口径。

如果基准日为 `2026-03-13`，且当日 `latest_adj_factor = 230.3931`：

```text
qfq_factor = 224.7531 / 230.3931
qfq_close = 40.76 * qfq_factor = 39.762199
hfq_factor = 224.7531
hfq_close = 40.76 * 224.7531 = 9160.936356
```

## 5. 非价格字段

以下字段保持原始口径，不做复权：

- `pct_chg`
- `vol`
- `amount`

原因：

- `pct_chg` 是比例字段，不需要再乘价格复权因子。
- `vol` 是成交量，不属于价格。
- `amount` 是成交额，不按价格复权因子调整。

## 6. 分钟线因子补齐

分钟线源文件当前没有 `adj_factor`。

导入 `1m` 和 `5m` 时需要按以下键补齐因子：

```text
code + date
```

优先来源：

1. 共享盘日线 `1d_price.zip` 中同 `code/date` 的 `adj_factor`
2. Tushare 代理 `adj_factor` 接口

补齐后生成：

```text
hfq_factor = adj_factor
qfq_factor = adj_factor / latest_adj_factor
```

缺少因子的记录不应进入正式行情表，需要进入待补因子或异常审计流程。

## 7. 查询示例

查询原始价：

```sql
select code, date, close
from market_data_1d
where dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

查询前复权价：

```sql
select code, date, qfq_close, qfq_factor
from market_data_1d
where dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

查询后复权价：

```sql
select code, date, hfq_close, hfq_factor
from market_data_1d
where dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

## 8. 注意事项

- 查询方看到 `open/high/low/close/pre_close/change/vwap` 时，应理解为原始价格。
- 查询方需要固定前复权口径时，优先查询 ClickHouse `market_data_*_qfq_cache` 表中的 `qfq_*` 字段。
- 查询方需要固定后复权口径时，使用 `hfq_*` 字段。
- 动态复权应基于原始价格和因子重新计算，不要对 `qfq_*` 或 `hfq_*` 再次复权。
- 不同基准日会生成不同的 `qfq_factor`，全量导入前需要固定基准日策略。
- 当前只保留 A 股股票 `1d`、`1m`、`5m` 三类数据，不导入指数、ETF、可转债等非股票数据。
