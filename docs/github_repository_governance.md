# 公共 GitHub 仓库治理方案

> 适用场景：使用公共 GitHub 仓库统一管理当前量化系统代码，同时把真实数据和密钥继续保留在 101 数据节点。

---

## 1. 核心结论

可以使用公共 GitHub 仓库做代码管理，但仓库定位必须是：

```text
代码治理仓库
```

不是：

```text
数据仓库
密钥仓库
生产配置仓库
数据库备份仓库
```

推荐职责划分：

```text
GitHub:
  代码、文档、migration、DDL、测试、配置样例、小样本 fixture

Mac:
  开发、Codex、IDE、本地单元测试、小样本验证

101:
  PostgreSQL、ClickHouse、MinIO、真实行情数据、导入任务、远程 smoke test
```

---

## 2. 推荐仓库结构

```text
Quant-System/
  packages/
    quant_contracts/
  services/
    quant_data_hub/
    quant_factor_lab/
    quant_factor_validation/
  clients/
    quant_data_sdk/
  infra/
    local/
    remote_101/
  docs/
    references/
      legacy_data_ingestion/
  tests/
```

说明：

- `packages/quant_contracts` 保存公共协议。
- `services/quant_data_hub` 后续迁入 101 旧项目的数据接入服务代码。
- `clients/quant_data_sdk` 从旧项目中抽出，供研究员和其他服务调用。
- `infra/remote_101` 只放部署样例和 systemd/docker compose 模板，不放真实 `.env`。
- `docs/references/legacy_data_ingestion` 保存旧项目文档、DDL 和 migration 参考。

---

## 3. 允许提交

```text
Python 源码
测试代码
README / docs
Alembic migration
ClickHouse DDL
Dockerfile
docker-compose.yml
.env.example
Makefile
小型 fixture
接口 schema
OpenAPI 说明
```

小型 fixture 原则：

- 不包含真实敏感客户信息。
- 不包含真实 token。
- 数据量足够单元测试即可。
- 文件尽量小于 5MB。

---

## 4. 禁止提交

```text
.env
真实 token
数据库密码
MinIO access key / secret key
券商密钥
Tushare token
PostgreSQL 数据目录
ClickHouse 数据目录
MinIO 数据目录
数据库 dump
真实行情大文件
真实研究产物大文件
日志文件
.venv
__pycache__
```

如果需要保存大文件索引，只提交 manifest，不提交文件本体：

```text
object_key
etag
size
created_at
data_source
data_version
```

---

## 5. 分支策略

第一阶段建议简单：

```text
main      # 可运行、测试通过
feature/* # 单个功能或服务迁移
docs/*    # 文档更新
```

合并前最低要求：

```text
python -m unittest
ruff check .
docker compose config
```

涉及数据库结构变更时必须同时包含：

```text
SQLAlchemy model 更新
Alembic migration
回滚说明
测试或手动验证记录
```

---

## 6. GitHub Actions 策略

公共仓库中的 CI 不能依赖真实 101 密钥。

第一阶段只运行：

```text
单元测试
ruff
类型检查，可选
docker compose config
```

不在公共 CI 中直接连接：

```text
101 PostgreSQL
101 ClickHouse
101 MinIO
Tushare
券商接口
```

需要远程验证时，采用手动 smoke test：

```text
ssh 192.168.2.101
cd /home/ddd/ZeTa-quant-data-ingestion-layer 或后续部署目录
运行远程测试 / 查询 / 导入 dry-run
```

---

## 7. 密钥策略

真实配置只允许存在于：

```text
101 节点 .env
本机未提交的 .env.local
部署平台 secret
密码管理器
```

仓库中只允许出现：

```text
.env.example
.env.remote.example
```

示例配置必须使用占位符：

```env
TUSHARE_TOKEN=replace_with_token
POSTGRES_PASSWORD=replace_with_password
MINIO_SECRET_KEY=replace_with_secret
```

---

## 8. 迁移代码前检查清单

从 101 旧项目迁移代码前，先检查：

- 是否包含 `.env` 读取逻辑但不会打印密钥。
- 是否把真实路径写死到代码中。
- 是否依赖 101 本机路径，例如 `/home/ddd/...`。
- 是否可以通过环境变量配置 PostgreSQL、ClickHouse、MinIO。
- 是否有对应 unittest。
- 是否有 `.env.example`。
- 是否会把大数据下载到 Mac。

迁移后必须确认：

```text
本地测试不需要真实数据
远程 smoke test 只读或 dry-run
真实数据仍保留在 101
```

