# 101 只读 Smoke Test

> 目标：验证 Mac 本地 `quant_data_hub` 容器可以通过 API 只读查询 101 节点 ClickHouse，不复制真实数据到本地。

---

## 1. 前提

101 节点保留真实数据和 ClickHouse：

```text
192.168.2.101
ClickHouse HTTP: 127.0.0.1:18123 on 101
```

Mac 本地通过 SSH tunnel 暴露本机端口：

```bash
make remote-101-clickhouse-tunnel
make remote-101-clickhouse-tunnel-status
```

容器内通过：

```text
http://host.docker.internal:18123
```

访问 Mac 上的 tunnel。

---

## 2. 本地私有配置

`.env` 是本地私有文件，已被 `.gitignore` 忽略。

需要配置：

```text
CLICKHOUSE_HTTP_URL=http://host.docker.internal:18123
CLICKHOUSE_DATABASE=quant_market
CLICKHOUSE_USER=quant
CLICKHOUSE_PASSWORD=<101 ClickHouse password>
```

不要提交 `.env`，不要把真实密码写入文档或 README。

---

## 3. 启动服务

```bash
make quant-data-hub-up
make quant-data-hub-check
```

预期：

```json
{"status":"ok","service":"quant-data-hub"}
```

---

## 4. 运行只读验证

```bash
make smoke-quant-data-hub-101
```

验证内容：

```text
GET  /health
GET  /api/v1/adjustments/qfq-batches?limit=3
POST /api/v1/market-bars/query raw 1d sample
POST /api/v1/market-bars/query qfq 1d sample
```

约束：

- 只读查询。
- 不导出数据文件。
- 不写 PostgreSQL、ClickHouse 或 MinIO。
- 不打印密码、token、access key。
