# quant-data-ingestion-layer 开发与生产方案

## 1. 当前业务边界

当前项目定位为批量行情数据入库与查询服务。

已确认边界：

- 暂不处理秒级数据
- 当前最高频率为每分钟数据
- 后续不做实时导入
- 第三方购买的数据先落到本地共享盘
- 本服务负责将共享盘数据批量同步到 PostgreSQL
- PostgreSQL 供内部人员、Codex、DBeaver 查询与计算使用
- 历史分钟级数据预计约 3T
- 行情表中的价格字段存储复权后价格
- 每条行情记录需要保留对应 `adj_factor`

## 2. 开发验证方案

开发验证阶段只使用 101 单节点。

```text
101 节点
├─ FastAPI 服务
├─ PostgreSQL
├─ Python .venv
├─ systemd --user 服务
└─ DBeaver / Codex 查询验证
```

开发验证阶段目标：

- 完成 FastAPI 项目骨架
- 完成 PostgreSQL 连接
- 完成 Alembic migration
- 完成分钟级行情数据模型
- 完成 staging 表和正式分区表
- 完成共享盘文件批量导入流程
- 完成复权因子补充和价格复权入库规则
- 完成 ingestion job 记录
- 完成基础查询接口
- 完成 `unittest` 测试

开发阶段暂不实现：

- 秒级数据
- 实时数据接入
- PostgreSQL 主从部署
- 高可用自动切换
- 复杂分析计算

## 3. 开发阶段数据流

```text
共享盘样本数据
    ↓
101 FastAPI / 导入脚本
    ↓
字段校验、时间标准化、空值处理
    ↓
PostgreSQL staging 表
    ↓
COPY / 批量写入
    ↓
PostgreSQL 分区正式表
    ↓
内部读取验证
```

开发阶段数据库连接：

```env
WRITE_DATABASE_URL=postgresql+asyncpg://quant_ingestion_app:***@localhost:5432/quant_data_ingestion
READ_DATABASE_URL=postgresql+asyncpg://quant_ingestion_app:***@localhost:5432/quant_data_ingestion
```

开发阶段可以让读写连接都指向 101 本机 PostgreSQL。

## 4. 生产方案

生产阶段采用 PostgreSQL 主从结构，隔离批量导入和内部查询压力。

```text
第三方数据文件
        ↓
本地共享盘
        ↓
101 主库节点
  FastAPI / 导入任务服务
  PostgreSQL Primary
  批量校验、标准化、COPY 入库
        ↓ PostgreSQL Streaming Replication
102 查询节点
  PostgreSQL Replica
  内部人员 / Codex / DBeaver / 查询接口
```

## 5. 生产职责划分

101 Primary：

- 共享盘文件批量导入
- 数据清洗和校验
- staging 表写入
- 正式分区表写入
- Alembic migration
- ingestion job 记录
- PostgreSQL 主库

102 Replica：

- 只读查询
- 内部人员读取
- Codex 查询
- DBeaver 查询
- 查询 API
- 后续可作为备份和容灾基础

数据库约束原则：

- 行情大表不使用外键
- 维表关系通过字段约定和导入校验保证
- 大批量导入优先保证吞吐
- 数据一致性通过 ingestion job、导入前校验和离线审计 SQL 保证

## 6. 应用配置

应用层保留读写分离配置。

```env
WRITE_DATABASE_URL=postgresql+asyncpg://quant_writer:***@101:5432/quant_data_ingestion
READ_DATABASE_URL=postgresql+asyncpg://quant_reader:***@102:5432/quant_data_ingestion
```

写入和导入逻辑只使用 `WRITE_DATABASE_URL`。

查询逻辑默认使用 `READ_DATABASE_URL`。

开发阶段可以让两个连接都指向 101。生产阶段将查询连接切到 102。

## 7. 数据导入流程

```text
共享盘数据文件
    ↓
创建 ingestion_job
    ↓
读取 CSV / Parquet / 第三方文件格式
    ↓
字段校验、时间标准化、空值处理
    ↓
COPY 到 staging 表
    ↓
去重 / upsert / 写入正式分区表
    ↓
ANALYZE
    ↓
记录导入结果
```

3T 历史数据导入建议：

- 按月份或日期分批
- 优先使用 PostgreSQL `COPY`
- 先导入，再补必要索引
- 每批导入后执行 `ANALYZE`
- 失败文件支持重试
- 导入期间监控主从复制延迟

## 8. 表结构策略

核心表：

```text
datasets
market_data_1m
ingestion_jobs
ingestion_files
staging_market_data_1m
```

`market_data_1m` 使用时间分区。

建议分区策略：

```text
按月 range partition
```

基础唯一约束：

```sql
(dataset_id, symbol, trade_time)
```

基础查询索引：

```sql
(dataset_id, symbol, trade_time)
(dataset_id, trade_time)
```

查询约束建议：

- 尽量必须带 `dataset_id`
- 尽量必须带 `trade_time` 范围
- 按 `symbol` 或 symbol 列表查询
- 避免无条件全表扫描

## 9. 存储规划

101 主库：

```text
SSD / NVMe:
  Ubuntu
  FastAPI 项目
  Python .venv
  PostgreSQL 配置
  PostgreSQL WAL，推荐

HDD RAID5:
  PostgreSQL data_directory
  3T 历史分钟级行情数据
```

102 从库：

```text
优先 SSD / NVMe 数据盘
如果成本限制，可用 HDD RAID
查询性能优先时，RAID10 优于 RAID5
```

WAL 建议：

- 优先放 SSD / NVMe
- 不建议和大容量 HDD RAID5 混放

## 10. 节点配置建议

101 主库，写入和导入：

```text
CPU: 8 核起步，推荐 12 到 16 核
内存: 32GiB 起步，推荐 64GiB
系统盘: SSD / NVMe 256GiB+
WAL 盘: SSD / NVMe 200GiB+
数据盘: 8 HDD RAID5 / RAID6 / RAID10
网络: 千兆起步，推荐万兆
```

102 从库，查询：

```text
CPU: 12 到 16 核
内存: 64GiB 起步，推荐 128GiB
数据盘: SSD / NVMe 优先
网络: 推荐万兆
```

如果 IT 优先增加一类资源，建议优先增加 102 查询节点内存。

原因：

- 历史行情查询依赖缓存
- 内存越大，PostgreSQL 能缓存更多索引和热数据
- 查询节点比写入节点更吃内存

## 11. PostgreSQL 主从方案

使用 PostgreSQL 物理流复制。

101 Primary：

```text
wal_level = replica
max_wal_senders
max_replication_slots
hot_standby = on
replication slot
```

102 Replica：

```text
pg_basebackup 初始化
standby.signal
primary_conninfo
primary_slot_name
```

主从收益：

- 导入和查询隔离
- 查询不直接压主库
- 主库写入更稳定
- 内部人员只读更安全
- 后续可扩展更多只读副本
- 具备基础容灾能力

注意：

- 主从不会让单条 SQL 自动变快
- 单条查询速度仍取决于从库硬件、内存、磁盘、索引、分区和 SQL

## 12. PostgreSQL 参数方向

101 主库，64GiB 内存示例：

```conf
shared_buffers = 8GB
effective_cache_size = 40GB
work_mem = 16MB
maintenance_work_mem = 1GB
max_connections = 50

wal_buffers = 16MB
checkpoint_timeout = 15min
checkpoint_completion_target = 0.9
max_wal_size = 16GB
min_wal_size = 4GB
```

102 查询库，64GiB 到 128GiB 内存示例：

```conf
shared_buffers = 8GB 到 16GB
effective_cache_size = 40GB 到 96GB
work_mem = 32MB 起，按并发控制
maintenance_work_mem = 1GB
max_connections = 50
```

具体参数必须根据最终机器配置和压测结果调整。

## 13. 当前落地顺序

1. 101 继续作为开发验证节点。
2. FastAPI 改成 `WRITE_DATABASE_URL` / `READ_DATABASE_URL` 双连接。
3. 实现 `market_data_1m` 分区表、staging 表、ingestion job。
4. 实现共享盘文件批量导入和 COPY 入库。
5. 准备 RAID5 数据盘和 PostgreSQL 数据目录迁移。
6. 准备 102 只读从库。
7. 配置 PostgreSQL streaming replication。
8. DBeaver / Codex / 查询接口切到 102。
9. 导入 3T 历史数据。
10. 压测导入速度、主从延迟和典型查询性能。

## 14. 当前结论

当前先实现开发验证方案：

```text
101 单节点
FastAPI + PostgreSQL
共享盘文件批量导入
分钟级数据
读写连接配置预留
```

生产目标方案：

```text
101 = Primary + 导入服务
102 = Replica + 查询服务
```

该方案适合当前“批量历史数据入库 + 内部持续高性能查询”的场景。
