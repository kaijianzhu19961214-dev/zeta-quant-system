# Zeta Quant System

模块化量化研究系统，覆盖行情数据接入、公共协议、因子计算、因子验证、回测、风控和研究产物管理。

A modular quantitative research system for market data, shared contracts, factor research, factor validation, backtesting, risk control, and research workflow orchestration.

---

## 项目定位 / Project Scope

`zeta-quant-system` 是量化研究平台的代码治理仓库。当前阶段优先建设一条稳定、可复现、可审计的 MVP 流水线：

`zeta-quant-system` is the code governance repository for a modular quantitative research platform. The current priority is a reproducible and auditable MVP pipeline:

```text
market data -> factor calculation -> factor validation report
```

当前采用的职责划分：

Current responsibility split:

```text
Mac / GitHub:
  code, docs, tests, migrations, small fixtures, development workflow

101 data node:
  PostgreSQL, ClickHouse, MinIO, real market data, ingestion jobs
```

真实行情数据、数据库目录、对象存储文件和密钥不进入公共仓库。

Real market data, database directories, object storage files, and secrets must not be committed to this public repository.

---

## 架构 / Architecture

推荐模块：

Planned modules:

```text
packages/
  quant_contracts/              # shared schemas, enums, errors, pure utilities

services/
  quant_data_hub/               # market data ingestion, storage, query, lineage
  quant_factor_lab/             # factor calculation
  quant_factor_validation/      # IC, Rank IC, grouping return, reports
  quant_model_lab/              # factor combination and signal generation
  quant_backtest_engine/        # portfolio simulation and performance metrics
  quant_risk_engine/            # portfolio constraints and risk adjustment
  quant_execution_gateway/      # paper/live execution gateway, later stage

clients/
  quant_data_sdk/               # Python SDK for market data and research artifacts

infra/
  local/                        # local development infrastructure
  remote_101/                   # 101 data node deployment templates
```

当前仓库已建立 monorepo 目录骨架，并已落地 `quant_contracts` 公共协议包和 `quant_data_hub` 第一批行情查询服务代码。业务服务代码会继续分阶段迁入。

The repository now includes the monorepo directory scaffold, `quant_contracts`, the first `quant_data_hub` market-query service code, local container infrastructure, and reference materials from the existing 101 data-ingestion project. Service code will continue to be migrated in phases.

---

## 数据架构 / Data Architecture

`quant_data_hub` 的生产形态采用三层数据基础设施：

`quant_data_hub` uses a three-part production data infrastructure:

```text
PostgreSQL:
  control plane, metadata, ingestion jobs, lineage, small validation tables

ClickHouse:
  main analytical store for raw/qfq/hfq market data

MinIO:
  raw files, intermediate artifacts, factor outputs, research reports
```

101 节点已有验证环境，详见：

The 101 node already hosts a validated data environment. See:

- [101 旧数据接入项目重合分析与迁移清单](docs/legacy_data_ingestion_overlap_and_migration.md)
- [quant_contracts 与旧项目协议映射](docs/quant_contracts_legacy_mapping.md)
- [旧项目参考材料](docs/references/legacy_data_ingestion/README_IMPORT.md)

---

## 快速开始 / Quick Start

本地只启动轻量基础设施：

Start the lightweight local infrastructure:

```bash
make infra-up
make infra-check
```

查看状态：

Check service status:

```bash
make infra-ps
```

停止本地基础设施：

Stop local infrastructure:

```bash
make infra-down
```

当前本地 Compose 只包含：

Current local Compose services:

```text
PostgreSQL 16
Redis 7
```

大规模 PostgreSQL、ClickHouse、MinIO 和真实行情数据继续留在 101 节点。

Large PostgreSQL, ClickHouse, MinIO, and real market data stay on the 101 node.

---

## 配置 / Configuration

复制 `.env.example` 后再本地修改：

Copy `.env.example` before local customization:

```bash
cp .env.example .env
```

不要提交 `.env`。

Do not commit `.env`.

仓库只允许保存配置样例：

Only example configuration files are allowed:

```text
.env.example
.env.remote.example
```

真实配置应保存在 101 节点、本机未提交文件、部署平台 secret 或密码管理器中。

Real configuration should live on the 101 node, untracked local files, deployment secrets, or a password manager.

---

## 文档 / Documentation

核心文档：

Core documents:

- [量化多项目架构与 Codex 实施方案](docs/quant_multi_project_codex_plan.md)
- [容器部署与服务编排方案](docs/container_deployment_and_orchestration.md)
- [公共 GitHub 仓库治理方案](docs/github_repository_governance.md)
- [Python 运行时策略](docs/python_runtime_policy.md)
- [101 旧数据接入项目重合分析与迁移清单](docs/legacy_data_ingestion_overlap_and_migration.md)
- [quant_contracts 与 101 旧数据接入项目协议映射](docs/quant_contracts_legacy_mapping.md)

---

## 安全边界 / Security Boundary

允许提交：

Allowed:

```text
code
docs
tests
Alembic migrations
ClickHouse DDL
Dockerfile / docker-compose examples
.env.example
small fixtures
```

禁止提交：

Forbidden:

```text
.env
real tokens
database passwords
MinIO access keys
broker credentials
PostgreSQL data directories
ClickHouse data directories
MinIO data directories
database dumps
large market data files
logs
.venv
__pycache__
```

---

## 开发与验证 / Development And Validation

第一阶段最低检查：

Minimum first-stage checks:

```bash
make test
ruff check .
docker compose config
```

当前项目采用容器优先策略，MVP 服务镜像默认使用 `python:3.12.13-slim`，详见 [Python 运行时策略](docs/python_runtime_policy.md)。

The MVP runtime is container-first and defaults to `python:3.12.13-slim`. See [Python runtime policy](docs/python_runtime_policy.md).

---

## 路线图 / Roadmap

第一阶段：

Phase 1:

```text
1. implement shared schemas in packages/quant_contracts
2. migrate 101 data-ingestion code into services/quant_data_hub
3. extract quant_data_sdk into clients/quant_data_sdk
4. keep real data on 101 and use API / read-only access for validation
```

第二阶段：

Phase 2:

```text
1. implement quant_factor_lab
2. implement quant_factor_validation
3. generate factor validation reports
4. add controlled remote smoke tests against 101
```

后续阶段：

Later phases:

```text
model lab
backtest engine
risk engine
execution gateway
```

---

## License

待定。

To be decided.
