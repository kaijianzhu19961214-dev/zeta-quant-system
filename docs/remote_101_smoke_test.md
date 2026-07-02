# 101 只读 Smoke Test

> 目标：验证 Mac 本地服务可以只读查询 101 节点数据与研究产物，不复制真实数据到本地。

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

---

## 5. 运行真实因子流转只读验证

```bash
make smoke-real-factor-flow-101
```

默认验证内容：

```text
1. 调用 quant_factor_lab /api/v1/factors/calculate
2. 从 101 ClickHouse 读取 2026-06-01 至 2026-06-10 的 qfq 日线小样本
3. 计算 technical.momentum / momentum_1d
4. 调用 quant_factor_validation /api/v1/factors/validate
5. 输出 IC / Rank IC / ICIR 和 manifest artifact 数量
```

默认样本：

```text
symbols: 000001.SZ,000651.SZ,000333.SZ,600000.SH,600519.SH
price_mode: qfq
batch_id: qfq_20260610
run_id: real_flow_smoke_101
```

约束：

- 只读查询 101 ClickHouse。
- 不写 PostgreSQL、ClickHouse 或 MinIO。
- 不打印明细行情、密码、token、access key。
- 输出只包含行数、有效样本数和验证指标摘要。

---

## 6. 启动 Ops API / Web 只读产物联调

`quant_ops_api` / `quant_ops_web` 可以通过本地 SSH tunnel 读取 101 节点上的 PostgreSQL task/artifact ledger 和 MinIO `factor_comparison_report.v1` 产物。

一键启动：

```bash
make quant-ops-101-readonly-up
```

该命令会：

```text
1. 打开 PostgreSQL tunnel: 127.0.0.1:15433 -> 101:5432
2. 打开 MinIO tunnel:      127.0.0.1:19001 -> 101:9000
3. 打开 ClickHouse tunnel: 127.0.0.1:18123 -> 101:18123
4. 从 101 节点读取远程 env，并只在当前 shell 进程中注入必要配置
5. 重启 quant_ops_api / quant_ops_web
6. 运行 factor_comparison_report.v1 artifact smoke test
```

默认验证目标：

```text
artifact_read_status: artifact_loaded
source: object_store_factor_comparison_report
artifact_id: validation_smoke_101_codex_comparison_report
factor_name: smoke_momentum_1d
```

打开页面：

```text
http://127.0.0.1:18040
```

运行约束：

- 只读 PostgreSQL 和 MinIO。
- 不把 101 节点真实 env 写入本地文件。
- 不把密码、token、access key 打印到终端或提交到 Git。
- 不复制大规模行情数据到 Mac。
- `RUN_SMOKE=0 make quant-ops-101-readonly-up` 可只启动服务，不执行 smoke。
