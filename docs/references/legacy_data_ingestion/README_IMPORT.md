# legacy_data_ingestion 参考材料说明

来源：

```text
192.168.2.101:/home/ddd/ZeTa-quant-data-ingestion-layer
```

同步时间：

```text
2026-06-25
```

本目录只保存旧项目的结构、文档、DDL 和 migration 参考，不保存真实数据和密钥。

已同步：

```text
README.md
docs/
deploy/clickhouse/.env.example
deploy/clickhouse/docker-compose.yml
deploy/clickhouse/initdb/001_market_data.sql
alembic/versions/*.py
```

已排除：

```text
.env
.venv
__pycache__
*.pyc
PostgreSQL 数据目录
ClickHouse 数据目录
MinIO 数据目录
真实行情数据文件
真实 token / 密码 / secret
```

用途：

- 作为 `quant_data_hub` 的历史实现参考。
- 对照当前新架构中的数据接入、复权、查询、任务产物血缘设计。
- 后续迁移代码前，先确认字段命名、存储边界和 API 契约。

