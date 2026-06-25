# local infra / 本地基础设施

`infra/local` 保存 Mac 本地开发环境需要的基础设施配置。本地环境只承担轻量开发和小样本验证。

`infra/local` stores local development infrastructure for Mac-based work.

## 当前策略 / Current Strategy

```text
Mac:
  code, tests, docs, lightweight PostgreSQL, Redis, small fixtures

101:
  production-like PostgreSQL, ClickHouse, MinIO, real market data
```

当前根目录 `docker-compose.yml` 已提供本地 PostgreSQL 和 Redis。

## 常用命令 / Commands

```bash
make infra-up
make infra-check
make infra-ps
make infra-down
```

## 约束 / Rules

- 不在 Mac 本地默认启动大体量 ClickHouse / MinIO 数据目录。
- 不把真实行情数据复制进仓库。
- 本地 `.env` 只用于开发，不能提交。
- 所有可提交配置必须是 `.env.example` 或模板文件。

