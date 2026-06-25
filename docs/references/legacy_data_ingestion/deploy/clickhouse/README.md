# ClickHouse 验证环境

用途：在 101 节点验证行情分析库和前复权缓存链路。

启动：

```bash
cd ~/ZeTa-quant-data-ingestion-layer/deploy/clickhouse
cp .env.example .env
docker compose up -d
```

如果 101 节点访问 Docker Hub 较慢，保持 `.env` 中的
`CLICKHOUSE_IMAGE=docker.1panel.live/clickhouse/clickhouse-server:24.8-alpine`。
若后续网络恢复正常，可以改回 `clickhouse/clickhouse-server:24.8`。

验证：

```bash
curl 'http://127.0.0.1:18123/?query=select%20version()'
docker exec -it clickhouse clickhouse-client --user quant --password
```

从项目脚本写入验证数据：

```bash
cd ~/ZeTa-quant-data-ingestion-layer
. .venv/bin/activate
python scripts/sync_pg_to_clickhouse.py --timeframe all --chunk-size 20000
```

端口：

- HTTP: `18123`
- Native TCP: `19000`

注意：

- 101 上已有 MinIO 占用 `9000/9001`，所以 ClickHouse native 端口映射为 `19000`。
- 当前为单节点验证配置；生产环境需要单独规划数据盘、备份、监控和副本。
