# quant-data-ingestion-layer

量化数据接入层服务，负责接收、校验、标准化并落库第三方量化数据。

## 本地运行

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 健康检查

```bash
curl http://127.0.0.1:8000/health
```

## ClickHouse 样本同步

把 PostgreSQL 当前验证数据同步到 ClickHouse raw 表：

```bash
python scripts/sync_pg_to_clickhouse.py --timeframe all --chunk-size 20000
```

从共享盘直接导入指定交易日到 ClickHouse：

```bash
python scripts/import_shared_market_data_to_clickhouse.py \
  --shared-root /Volumes/nfs/data/A股分钟数据 \
  --timeframe all \
  --date 20260313 \
  --replace-day
```

如果脚本在 101 节点运行，共享盘建议挂载为 `/mnt/nfs/data/A股分钟数据`。

生成前复权缓存批次：

```bash
python scripts/build_clickhouse_qfq_cache.py --timeframe all --replace
```
