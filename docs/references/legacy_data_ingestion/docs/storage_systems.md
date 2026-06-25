# 存储系统选型说明

## 1. 当前推荐组合

当前推荐：

```text
PostgreSQL：关系型控制面
MinIO：对象存储和原始数据湖
ClickHouse：行情分析库和高速查询层
```

101 节点先容器化部署 ClickHouse 做流程验证；生产环境再把 PostgreSQL、ClickHouse、MinIO 的数据目录迁移到正式数据盘。

## 2. PostgreSQL

作用：

- 元数据
- 导入任务
- 用户和权限
- 交易日历
- 股票基础信息
- 复权因子
- 前复权批次
- 开发验证阶段的小规模行情表

优势：

- SQL 标准和生态成熟。
- 事务、约束、权限、审计能力强。
- DBeaver 等工具支持很好。
- 适合控制面和一致性要求高的数据。

劣势：

- 超大分钟行情表持续 UPDATE 压力大。
- 3T 到 7T 级行情分析查询不是它最擅长的场景。
- 对全市场长区间扫描、聚合、回测类查询，行式存储成本较高。

结论：

PostgreSQL 不作为最终行情分析主引擎，只作为控制面和验证库。

## 3. MinIO

作用：

- 原始 zip/parquet 归档
- 中间 parquet 文件
- 导入失败样本
- 月度缓存产物
- 备份

优势：

- S3 协议兼容。
- 适合保存大文件和不可变数据。
- 可作为 ClickHouse、Spark、Python 批处理的数据入口。
- 与 Docker 部署结合简单。

劣势：

- 不是低延迟 SQL 查询引擎。
- 不负责事务型数据一致性。
- 需要额外元数据系统记录文件状态。

结论：

MinIO 负责“存文件”和“数据湖入口”，不直接承担研究查询。

## 4. ClickHouse

作用：

- A 股 `1d`、`1m`、`5m` 行情分析库
- 原始行情高速查询
- 后复权视图
- 月度前复权缓存表
- 全市场扫描、聚合、回测数据读取

优势：

- 列式存储，适合只读少数字段的大范围扫描。
- 压缩率高，适合历史行情。
- MergeTree 支持按时间分区和按查询键排序。
- SQL 友好，DBeaver 也能连接。
- 可以通过 S3 table function 或 S3 集成读取 MinIO 数据。
- 官方 Docker 镜像部署简单。

劣势：

- 不适合复杂事务。
- 不适合作为主业务元数据库。
- UPDATE/DELETE 不是强项，设计上应尽量 append-only。
- 表设计需要提前根据查询模式规划 `PARTITION BY` 和 `ORDER BY`。

结论：

ClickHouse 是当前 101 验证和后续生产开源方案的首选分析库。

## 5. DolphinDB

作用：

- 金融时序数据库
- 因子研究
- 流批一体
- 行情数据分析

优势：

- 面向金融场景能力强。
- 时序和矩阵计算能力强。
- 适合量化研究、因子计算和回测平台。
- 国内金融机构认知度较高。

劣势：

- 商业属性更强，需要考虑授权和运维经验。
- 与现有 Python/FastAPI/PostgreSQL/MinIO 链路整合需要额外评估。
- 团队学习成本高于 ClickHouse。

结论：

如果后续预算、授权和团队经验允许，DolphinDB 可以作为更金融专用的候选方案；当前验证先不引入。

## 6. kdb+

作用：

- 高频行情
- tick 数据
- 低延迟金融时间序列

优势：

- 海外金融机构和交易场景中历史很深。
- tick 和高频时间序列能力强。
- 性能和表达力都很强。

劣势：

- 商业授权成本高。
- q 语言学习成本高。
- 与当前 Python/FastAPI/PostgreSQL 团队栈差异大。

结论：

kdb+ 是金融高频领域的经典方案，但不适合作为当前内部验证阶段的第一选择。

## 7. TimescaleDB

作用：

- PostgreSQL 生态内的时序扩展

优势：

- 保留 PostgreSQL SQL、驱动、权限和生态。
- hypertable、压缩、保留策略适合时序数据。
- 学习成本低于引入全新数据库。

劣势：

- 本质仍基于 PostgreSQL 生态。
- 对 3T 到 7T 级全市场分钟行情分析，列式库通常更合适。
- 如果已经有 PostgreSQL，再引入 TimescaleDB 与 ClickHouse 的定位容易重叠。

结论：

TimescaleDB 是 PostgreSQL 增强路线；如果想尽量少引入组件可以考虑，但当前更推荐 ClickHouse 承担分析查询。

## 8. InfluxDB

作用：

- 监控指标
- IoT 时序
- DevOps 指标

优势：

- 时序写入和指标查询体验好。
- 生态适合监控和仪表盘。

劣势：

- 股票分钟线是高基数、多字段、复杂 SQL/回测查询场景。
- code、频率、市场、批次等维度容易形成高基数压力。
- 对量化研究人员，SQL/列式分析库通常更顺手。

结论：

本项目不优先使用 InfluxDB。

## 9. MySQL

作用：

- 普通业务关系库

优势：

- 部署简单。
- 运维普及度高。
- 适合传统业务数据。

劣势：

- 不适合 3T 到 7T 级历史行情分析主库。
- 分区、分析查询、列式压缩能力不如专门分析库。

结论：

当前已有 PostgreSQL，没必要换 MySQL。

## 10. 最终建议

101 验证阶段：

```text
PostgreSQL + MinIO + ClickHouse 单节点 Docker
```

生产阶段：

```text
PostgreSQL：控制面
MinIO：原始数据和中间产物
ClickHouse：行情分析与前复权缓存
7T HDD 阵列：先承载数据
SSD/NVMe：如果有，优先放 WAL、临时目录或 ClickHouse 热数据
```

后续如查询压力继续上升，再评估：

```text
DolphinDB
kdb+
ClickHouse 集群
```

容量规划和给 IT 的硬盘建议见：

```text
docs/it_storage_capacity_plan.md
```

101 节点小样本 MinIO 数据湖验证方案见：

```text
docs/research_pilot_with_minio.md
```

## 11. 参考

- ClickHouse 官方 Docker 文档：https://clickhouse.com/docs/install/docker
- ClickHouse MergeTree 文档：https://clickhouse.com/docs/engines/table-engines/mergetree-family/mergetree
- ClickHouse S3 集成：https://clickhouse.com/docs/integrations/s3
- ClickHouse 分区建议：https://clickhouse.com/docs/engines/table-engines/mergetree-family/custom-partitioning-key
- TimescaleDB 官方说明：https://github.com/timescale/timescaledb
- InfluxDB 高基数说明：https://docs.influxdata.com/influxdb/v2/write-data/best-practices/resolve-high-cardinality/
- DolphinDB 官方说明：https://dolphindb.com/
