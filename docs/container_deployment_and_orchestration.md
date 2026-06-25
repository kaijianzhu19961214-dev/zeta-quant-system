# 容器部署与服务编排方案

> 适用范围：当前量化系统 MVP 与后续生产化迭代。目标是在 Mac 本地、CI/CD 和未来服务器环境中使用一致的镜像与服务编排方式，降低环境差异，避免第二版重做第一版。

---

## 1. 核心结论

项目从第一版开始使用容器化，但不要一开始引入 Kubernetes。当前阶段采用：

```text
Docker 兼容运行时
  ↓
docker compose
  ↓
PostgreSQL / Redis / 各 Python 服务
```

第一阶段先容器化基础依赖和已落地服务：

```text
postgres
redis
quant_data_hub
```

第二阶段随着 MVP 服务生成，再逐步加入：

```text
quant_factor_lab
quant_factor_validation
```

`quant_contracts` 是公共 Python 包，不作为常驻服务运行。

---

## 2. 本地推荐环境

Mac 本地推荐任一 Docker 兼容运行时：

```text
Docker Desktop
OrbStack
Colima
```

当前项目只依赖标准 Docker CLI 与 Compose：

```text
docker
docker compose
```

不绑定某一个具体厂商。只要能执行 `docker compose up -d` 即可。

如果本机使用 OrbStack，建议确认当前 Docker context：

```bash
orb status
docker context use orbstack
docker info
```

预期状态：

```text
OrbStack: Running
Docker context: orbstack
```

---

## 3. 编排范围

### 3.1 MVP 基础设施

```text
PostgreSQL 16
Redis 7
```

PostgreSQL 本地开发采用一个实例、多个数据库：

```text
quant_system                  # 默认管理库
quant_data_hub                # 数据接入服务库
quant_factor_lab              # 因子计算服务库
quant_factor_validation       # 因子验证服务库
```

生产环境可以拆成独立实例或独立集群，但服务边界不变。

### 3.2 后续服务编排

每个服务独立镜像、独立启动命令、独立健康检查：

```text
quant_data_hub:
  build: ./services/quant_data_hub/Dockerfile
  healthcheck: GET /health
  clickhouse: external URL by CLICKHOUSE_HTTP_URL

quant_factor_lab:
  build: ./quant_factor_lab
  depends_on:
    postgres:
      condition: service_healthy

quant_factor_validation:
  build: ./quant_factor_validation
  depends_on:
    postgres:
      condition: service_healthy
```

服务之间不能通过容器文件系统共享内部代码。跨服务通信只能使用：

```text
HTTP API
只读数据库视图
批量数据快照
消息队列，后续可选
```

---

## 4. 文件结构

```text
docker-compose.yml
.env.example
Makefile
infra/
  postgres/
    init/
      01_create_databases.sql
docs/
  container_deployment_and_orchestration.md
```

后续服务生成后，每个服务目录内再补：

```text
Dockerfile
.dockerignore
alembic/
alembic.ini
```

当前已落地：

```text
services/quant_data_hub/Dockerfile
```

---

## 5. 配置约束

- 仓库只提交 `.env.example`，不提交真实 `.env`。
- 本地开发可以使用 Compose 默认值启动。
- 生产环境必须通过 CI/CD 或部署平台注入环境变量。
- 不允许在镜像、代码、测试、notebook、README 中写入真实密钥。
- 数据库密码、第三方数据 API token、券商密钥必须独立注入。

核心环境变量：

```text
POSTGRES_HOST
POSTGRES_PORT
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_DB
REDIS_HOST
REDIS_PORT
QUANT_DATA_HUB_PORT
CLICKHOUSE_HTTP_URL
CLICKHOUSE_DATABASE
CLICKHOUSE_USER
CLICKHOUSE_PASSWORD
```

---

## 6. 常用命令

启动基础设施：

```bash
docker compose up -d postgres redis
```

启动 `quant_data_hub`：

```bash
make quant-data-hub-up
make quant-data-hub-check
```

查看服务状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs -f postgres redis
```

停止服务：

```bash
docker compose down
```

保留数据重新启动：

```bash
docker compose up -d
```

删除容器和本地数据卷：

```bash
docker compose down -v
```

`down -v` 会删除本地数据库数据，只能用于本地重置。

---

## 7. 健康检查

PostgreSQL 健康检查：

```bash
docker compose exec postgres pg_isready -U quant_admin -d quant_system
```

Redis 健康检查：

```bash
docker compose exec redis redis-cli ping
```

预期结果：

```text
PostgreSQL: accepting connections
Redis: PONG
```

---

## 8. 服务镜像约束

后续每个 Python 服务镜像必须满足：

- 使用 `python:3.12.13-slim` 作为 MVP 默认基础镜像。
- 只安装本服务运行所需依赖。
- 不复制其他服务的内部源码。
- 通过 `pip install -e ../quant_contracts` 或发布包方式使用公共协议。
- 启动前执行必要的 migration。
- 提供 `/health` 或等价健康检查接口。
- 容器日志输出到 stdout/stderr，由编排系统收集。

服务 Dockerfile 推荐结构：

```text
python:3.12.13-slim
  ↓
安装系统依赖
  ↓
安装 Python 依赖
  ↓
复制当前服务代码
  ↓
启动 FastAPI 或批处理入口
```

`quant_data_hub` 当前已经按这个结构构建镜像，启动入口为：

```text
python -m uvicorn quant_data_hub.main:app --host 0.0.0.0 --port 8000
```

---

## 9. 数据与迁移约束

- 每个服务只迁移自己拥有的数据库对象。
- 数据库变更必须通过 Alembic migration。
- 不允许服务在启动时隐式创建生产表。
- 本地初始化脚本只负责创建开发数据库，不负责创建业务表。
- 业务表由各服务自己的 migration 管理。
- 关键业务表必须包含 `created_at`、`updated_at`，关键计算结果必须包含 `run_id`。

---

## 10. 本地到生产的演进路径

阶段 1：本地基础设施

```text
docker compose 启动 postgres / redis
```

阶段 2：MVP 服务容器化

```text
quant_data_hub
quant_factor_lab
quant_factor_validation
```

阶段 3：CI 构建镜像

```text
unittest
ruff
build image
push image
```

阶段 4：服务器部署

```text
docker compose 或轻量编排平台
```

阶段 5：更大规模生产部署

```text
Kubernetes / ECS / 云托管容器平台
```

只有当服务数量、部署频率、弹性扩缩容和权限隔离需求明显提高时，才需要进入阶段 5。

---

## 11. 故障恢复

本地容器异常时，优先按以下顺序处理：

```text
docker compose ps
docker compose logs -f postgres redis
docker compose restart postgres redis
docker compose down
docker compose up -d
```

只有确认本地数据可以丢弃时，才执行：

```bash
docker compose down -v
```

---

## 12. 验收标准

容器环境第一阶段验收：

```text
docker compose config --quiet 可以通过
postgres 容器状态为 healthy
redis 容器状态为 healthy
quant_data_hub /health 返回 ok
quant_data_hub / quant_factor_lab / quant_factor_validation 数据库已创建
pg_isready 返回 accepting connections
redis-cli ping 返回 PONG
```
