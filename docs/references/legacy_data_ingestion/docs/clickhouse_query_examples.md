# ClickHouse 查询示例

## 1. 当前库和表

```sql
select name
from system.tables
where database = 'quant_market'
order by name;
```

查看三张 raw 表行数：

```sql
select '1d' as timeframe, count()
from quant_market.market_data_1d_raw
union all
select '1m' as timeframe, count()
from quant_market.market_data_1m_raw
union all
select '5m' as timeframe, count()
from quant_market.market_data_5m_raw
order by timeframe;
```

## 2. 原始价查询

日线原始价：

```sql
select code, date, open, high, low, close, vol, amount
from quant_market.market_data_1d_raw
where dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

分钟线原始价：

```sql
select code, trade_time, open, high, low, close, vol, amount
from quant_market.market_data_1m_raw
where dataset_code = 'a_share_1m'
  and code = '000001.SZ'
  and date = '2026-03-13'
order by trade_time;
```

## 3. 后复权查询

后复权通过 `v_market_data_*_hfq` 视图动态计算。

```sql
select code, date, close, hfq_factor, hfq_close
from quant_market.v_market_data_1d_hfq
where dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

```sql
select code, trade_time, close, hfq_factor, hfq_close
from quant_market.v_market_data_1m_hfq
where dataset_code = 'a_share_1m'
  and code = '000001.SZ'
  and date = '2026-03-13'
order by trade_time;
```

## 4. 前复权查询

先查看可用批次：

```sql
select batch_id, qfq_base_date, status, finished_at
from quant_market.qfq_batches
order by created_at desc;
```

当前验证批次：

```text
qfq_20260313
qfq_20260610
```

日线前复权：

```sql
select code, date, qfq_factor, qfq_close
from quant_market.market_data_1d_qfq_cache
where batch_id = 'qfq_20260313'
  and dataset_code = 'a_share_1d'
  and code = '000651.SZ'
order by date;
```

分钟线前复权：

```sql
select code, trade_time, qfq_factor, qfq_close
from quant_market.market_data_1m_qfq_cache
where batch_id = 'qfq_20260313'
  and dataset_code = 'a_share_1m'
  and code = '000001.SZ'
  and date = '2026-03-13'
order by trade_time;
```

## 5. 全市场日线验证

当前 101 节点已写入 `2026-06-01` 至 `2026-06-10` 的全市场日线。

查看日线覆盖：

```sql
select
    count() as rows,
    uniqExact(code) as codes,
    min(date) as min_date,
    max(date) as max_date
from quant_market.market_data_1d_raw
where dataset_code = 'a_share_1d';
```

查看最新交易日日线：

```sql
select code, date, open, high, low, close, vol, amount, adj_factor, source_name
from quant_market.market_data_1d_raw
where dataset_code = 'a_share_1d'
  and date = '2026-06-10'
order by code
limit 20;
```

查看后复权日线：

```sql
select code, date, close, hfq_factor, hfq_close, vol
from quant_market.v_market_data_1d_hfq
where dataset_code = 'a_share_1d'
  and date = '2026-06-10'
order by code
limit 20;
```

查看 `qfq_20260610` 前复权缓存：

```sql
select code, date, qfq_factor, qfq_close
from quant_market.market_data_1d_qfq_cache
where batch_id = 'qfq_20260610'
  and dataset_code = 'a_share_1d'
  and date = '2026-06-10'
order by code
limit 20;
```

测试页面：

```text
http://192.168.2.101:8000/node-tests
```

## 6. 典型过滤条件

按代码和时间范围：

```sql
select code, trade_time, close
from quant_market.market_data_1m_raw
where dataset_code = 'a_share_1m'
  and code = '000001.SZ'
  and trade_time >= '2026-03-13 09:30:00'
  and trade_time < '2026-03-13 15:00:00'
order by trade_time;
```

按交易日扫描全市场：

```sql
select code, trade_time, close, vol
from quant_market.market_data_5m_raw
where dataset_code = 'a_share_5m'
  and date = '2026-03-13'
order by code, trade_time;
```

## 7. 查询口径

- `market_data_*_raw`：原始价格和稳定因子。
- `v_market_data_*_hfq`：后复权动态视图。
- `market_data_*_qfq_cache`：按 `batch_id` 固定基准日的前复权缓存。
- `vol`、`amount`、`pct_chg` 不做价格复权。
