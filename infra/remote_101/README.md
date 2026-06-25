# remote_101 infra / 101 节点基础设施

`infra/remote_101` 保存 101 数据节点的部署模板、巡检说明和远程 smoke test 约定。

`infra/remote_101` stores deployment templates and operational notes for the 101 data node.

## 101 节点职责 / Responsibilities

```text
PostgreSQL:
  control plane, metadata, lineage

ClickHouse:
  production analytical market-data store

MinIO:
  raw files and research artifacts

Jobs:
  ingestion, adjustment, inventory inspection, smoke tests
```

## 约束 / Rules

- 可以提交模板、DDL、migration、巡检脚本和说明文档。
- 不能提交真实 `.env`、密码、token、MinIO key、数据库 dump 或大文件数据。
- 远程测试默认只读或 dry-run。
- 从 101 同步到 Mac 时，优先同步结构和经验，不同步全量真实数据。

## 参考材料 / References

- [旧项目参考材料](../../docs/references/legacy_data_ingestion/README_IMPORT.md)
- [101 旧数据接入项目重合分析与迁移清单](../../docs/legacy_data_ingestion_overlap_and_migration.md)

