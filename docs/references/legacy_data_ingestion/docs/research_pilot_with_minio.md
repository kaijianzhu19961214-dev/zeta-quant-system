# 101 小样本研究流程验证方案

## 1. 当前结论

101 节点当前剩余空间约 `71G`。

这个空间不适合导入全市场 5 年 `1m` 数据，也不适合复制 3T 原始数据湖。

但它足够验证：

```text
N 只股票 × 5 年 × 1d/1m/5m
共享盘原始数据抽取
MinIO 小样本数据湖
ClickHouse raw 表
ClickHouse qfq_cache
DBeaver / SDK 查询
PostgreSQL 任务与产物元数据
```

推荐先用 `10 - 100` 只股票做完整流程验证。

如果要做到 `500` 只股票 × 5 年，同时保留 MinIO 子集 parquet、ClickHouse raw、qfq_cache 和临时空间，`71G` 会比较紧。

## 2. 重要空间区别

### 不推荐：复制整年全市场 zip 到 MinIO

共享盘当前全市场 zip 大致为：

```text
1m_price_zip/2021.zip  3.4G
1m_price_zip/2022.zip  3.7G
1m_price_zip/2023.zip  3.8G
1m_price_zip/2024.zip  4.0G
1m_price_zip/2025.zip  4.3G

5m_price_zip/2021.zip  926M
5m_price_zip/2022.zip  1.0G
5m_price_zip/2023.zip  1.0G
5m_price_zip/2024.zip  1.1G
5m_price_zip/2025.zip  1.1G
```

如果把 2021-2025 的全市场 `1m + 5m + 1d` 原始 zip 全量复制进 MinIO，约需要 `25G+`。

这还没有包含：

- ClickHouse raw 表
- ClickHouse qfq_cache
- MinIO 中间 parquet
- ClickHouse merge 临时空间
- 日志和备份

所以在 101 当前 71G 空间下，不建议复制整年全市场 zip。

### 推荐：先抽取 N 只股票子集 parquet

流程：

```text
共享盘全量 zip
    ↓
抽取 N 只股票 × 指定年份
    ↓
写入 MinIO curated parquet
    ↓
导入 ClickHouse raw 表
    ↓
生成 qfq_cache
    ↓
研究员查询和回测
```

这样 MinIO 只保存验证子集，空间可控。

## 3. 5 年 1min 空间估算

估算参数：

```text
1 只股票 1 年 1min：约 6 万行
1 只股票 5 年 1min：约 30 万行
ClickHouse raw + 1 个 qfq_cache：约 70-210 字节/行
```

估算表：

| 股票数量 | 5 年 1min 行数 | ClickHouse raw + qfq_cache |
|---:|---:|---:|
| 1 | 30 万 | 约 21 MB - 63 MB |
| 10 | 300 万 | 约 210 MB - 630 MB |
| 50 | 1500 万 | 约 1.1 GB - 3.2 GB |
| 100 | 3000 万 | 约 2.1 GB - 6.3 GB |
| 200 | 6000 万 | 约 4.2 GB - 12.6 GB |
| 500 | 1.5 亿 | 约 10.5 GB - 31.5 GB |

如果同时保留：

- `5m`
- `1d`
- MinIO 子集 parquet
- 导入日志
- 失败样本
- ClickHouse merge 临时空间

建议按上表再乘 `2 - 3` 做预留。

在 101 当前约 71G 可用空间下：

```text
10 - 100 只股票 × 5 年：非常适合验证
200 只股票 × 5 年：可验证，但要控制 MinIO 产物和缓存批次数
500 只股票 × 5 年：接近上限，不建议作为第一轮
全市场 × 5 年：不建议在 101 上做
```

## 4. MinIO 小样本数据湖目录建议

Bucket：

```text
quant-factor-data
```

对象路径：

```text
raw_subset/a_share_1m/year=2021/codes_10.parquet
raw_subset/a_share_5m/year=2021/codes_10.parquet
curated/a_share_1m/year=2021/month=01/part-000.parquet
curated/a_share_5m/year=2021/month=01/part-000.parquet
manifests/research_pilot_20260618.json
failed_samples/research_pilot_20260618/
backtests/{strategy_name}/{run_id}/
reports/{strategy_name}/{run_id}/
```

说明：

- `raw_subset/` 保存从共享盘抽取出的研究验证子集。
- `curated/` 保存字段标准化后的 parquet。
- `manifests/` 保存文件清单、hash、股票池、年份、生成参数。
- `backtests/` 保存研究员回测交易明细、净值曲线等。
- `reports/` 保存 HTML/PDF/图片报告。

## 5. 当前上传验证结果

已完成一次从 Mac 共享盘到 101 MinIO 的小样本上传验证。

源目录：

```text
/Volumes/nfs/data/A股分钟数据/sample_5m_from_1m
```

MinIO：

```text
endpoint: 192.168.2.101:9000
bucket: quant-factor-data
```

已上传对象：

```text
pilot/shared_data/sample_5m_from_1m/parquet/20260105_5m_from_1m.parquet
pilot/shared_data/sample_5m_from_1m/csv/20260105_5m_from_1m.csv
manifests/shared_data_upload_smoke_test_20260618T170935.json
```

验证结论：

- 本机可以读取共享盘 `/Volumes/nfs/data/A股分钟数据`。
- 本机可以连接 101 节点 MinIO。
- `quant-factor-data` bucket 可创建或复用。
- Parquet、CSV、manifest 都可以正常写入并通过对象列表校验。

注意：

- 当前只上传了验证样本，没有把 3T 全量共享盘复制进 MinIO。
- 后续正式流程应按股票池、年份、频率抽取子集 parquet，再上传到 MinIO。
- MinIO 管理账号和密钥只作为服务端配置使用，不写入文档、不交给研究员侧 SDK。

## 6. PostgreSQL 任务记录

当前已有 `ingestion_jobs` 表，可记录行情导入任务。

当前 API / SDK 已落地：

```text
task_runs
task_artifacts
```

用途：

- `task_runs` 记录因子计算、回测、研究导出、样本准备等研究任务。
- `task_artifacts` 记录 MinIO 上的 parquet、csv、json、报告等文件产物。

详细字段见：

```text
docs/database_schema.md
```

## 7. 验证流程建议

第一轮建议：

```text
股票数量：10 - 50 只
年份：最近 5 年
频率：1d + 1m + 5m
MinIO：保存子集 parquet、manifest、回测结果
ClickHouse：保存 raw 表和 1 个 qfq_cache 批次
PostgreSQL：记录任务、批次、产物路径
```

第二轮建议：

```text
股票数量：100 - 200 只
年份：最近 5 年
重点验证：导入耗时、ClickHouse 查询、qfq_cache 生成、MinIO 产物管理
```

暂不建议：

```text
全市场 × 5 年
复制整年全市场 zip 到 MinIO
保留多个月度 qfq_cache 批次
```

## 8. 给研究员的使用方式

行情查询：

```text
DBeaver / Python SQL → ClickHouse
```

研究产物：

```text
Python SDK → FastAPI → MinIO presigned URL → 上传 parquet/report
```

任务记录：

```text
FastAPI → PostgreSQL task_runs / task_artifacts
```

最终体验：

```python
client = QuantDataClient.from_env()

bars = client.market.get_bars(
    codes=["000001.SZ", "000651.SZ"],
    timeframe="1m",
    start="2021-01-01",
    end="2025-12-31",
    price_mode="qfq",
    batch_id="qfq_20251231",
)

task = client.tasks.create(
    task_type="backtest",
    task_name="momentum_v1_run_001",
    input_params={"batch_id": "qfq_20251231"},
)

client.artifacts.upload_file(
    task_id=task["task_id"],
    artifact_type="backtest_trades",
    local_path="trades.parquet",
    object_key=f"backtests/momentum_v1/{task['task_id']}/trades.parquet",
)
```

SDK / API 的认证配置、环境变量和 Codex 提示词模板见：

```text
docs/sdk_api_design.md
```

## 9. 当前建议

101 当前还有约 `71G`，建议先不要追求大规模。

推荐下一步：

```text
1. 选定 10 - 50 只股票
2. 抽取 5 年 1d/1m/5m 子集 parquet
3. 上传子集 parquet 到 MinIO
4. 导入 ClickHouse raw 表
5. 生成 qfq_cache
6. 让研究员用 DBeaver / SDK 跑一次完整回撤验证
```
