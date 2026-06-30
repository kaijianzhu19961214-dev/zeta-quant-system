# 因子处理、验证与评分路线

> 面向对象：量化研究员、策略研究负责人和平台开发人员。本文用于统一当前项目的因子分类、外部库定位、验证评分路线和后续迭代边界。

---

## 1. 当前主链路

当前 MVP 主链路是：

```text
quant_data_hub
  ↓ 标准行情数据
quant_data_sdk
  ↓ Python 客户端
quant_factor_lab
  ↓ 因子值
quant_factor_validation
  ↓ IC / Rank IC / 分组收益 / 验证报告
quant_ops_api
  ↓ 只读聚合 API
quant_ops_web
  ↓ 研究员和运营监控页面
```

核心边界：

- `quant_data_hub` 是标准数据入口，负责字段映射、复权口径和数据查询。
- `quant_factor_lab` 只负责把标准数据或批准的研究快照转换成因子值。
- `quant_factor_validation` 负责因子验证、报告、manifest 和可持久化产物。
- `quant_ops_api` / `quant_ops_web` 只做只读聚合与展示，不直接写数据库或对象存储。
- 第三方原始数据可以通过只读 adapter 做研究兼容，但进入生产主链路前必须迁移到 `quant_data_hub` 或独立数据接入服务。

---

## 2. 因子分类口径

后续不要只按“股票 / 期货”切分因子，而要同时固定：

```text
asset_class     # equity / futures
factor_mode     # cross_sectional / time_series
factor_family   # price_volume / term_structure / fundamental / macro / model
```

建议分类：

| 资产 | 因子形态 | 因子族 | 典型因子 | 默认验证方式 | 参考库 |
| ---- | ---- | ---- | ---- | ---- | ---- |
| 股票 | `cross_sectional` | `price_volume` | 动量、反转、波动率、量比、价量相关 | IC、Rank IC、分组收益、多空收益、换手 | Alphalens、Qlib、OpenSourceAP/CrossSection |
| 股票 | `cross_sectional` | `fundamental` | 估值、盈利、成长、质量、资产定价特征 | 截面 IC、分组收益、行业/市值中性后表现 | OpenSourceAP/CrossSection、Qlib |
| 股票 | `cross_sectional` | `model` | ML alpha score、模型预测收益 | train/valid/test、IC、Rank IC、组合回测 | Qlib、MLflow |
| 期货 | `time_series` | `price_volume` | TSMOM、突破、均线、成交量冲击、波动率状态 | 单品种时序回测、Sharpe、回撤、胜率、换手 | vectorbt、commodity-curve-factors |
| 期货 | `cross_sectional` | `term_structure` | carry、期限结构 slope/curvature、跨品种动量 XSMOM | 跨品种排序、分组收益、Rank IC、板块中性 | commodity-curve-factors |

第一版当前只实现股票日频量价类截面因子中的 `momentum_*d`。期货时序因子、期货截面因子和股票 ML alpha 暂时不进入生产主链路，但协议和文档从第一版开始预留。

---

## 3. 外部库定位

这些库不作为项目的“大一统底座”，而是按方向作为研究引擎、benchmark 或 adapter 插件接入。所有输出必须映射回 `quant_contracts`。

| 库 / 项目 | 主要定位 | 在当前项目中的建议角色 | 接入边界 |
| ---- | ---- | ---- | ---- |
| [Alphalens](https://github.com/quantopian/alphalens) | 股票 alpha 因子表现分析，覆盖 returns、IC、turnover、grouped analysis | 股票截面因子验证 benchmark | 不直接替代 `quant_factor_validation`，只作为可复核引擎 |
| [Microsoft Qlib](https://github.com/microsoft/qlib) | AI-oriented quant platform，覆盖数据处理、模型训练和回测 | 股票截面研究流水线、Alpha158 / Alpha360、后续 `quant_model_lab` 参考 | 不直接接生产库密钥，不替代 `quant_data_hub` |
| [Qlib Alpha158 / Alpha360](https://github.com/microsoft/qlib/blob/main/examples/benchmarks/README.md) | Alpha158 偏人工设计表格因子，Alpha360 偏窗口特征 | 因子模板、Dataset / Processor 设计参考 | 输出必须转成标准 factor / evaluation 协议 |
| [vectorbt](https://github.com/polakowo/vectorbt) | 向量化回测和大规模参数实验 | 期货时序量价因子回测与参数扫描参考 | 不作为交易执行引擎 |
| [OpenSourceAP/CrossSection](https://github.com/OpenSourceAP/CrossSection) | 股票截面资产定价因子和可复现实验 | 股票基本面/资产定价特征库参考 | 仅引入因子定义和复现实验结构，不直接混入生产数据口径 |
| [commodity-curve-factors](https://github.com/brianbanna/commodity-curve-factors) | 商品期货期限结构、carry、slope、curvature、TSMOM / XSMOM | 期货期限结构和跨品种因子设计参考 | 作为研究形态参考，生产依赖前需单独评估成熟度 |
| [MLflow](https://mlflow.org/) | 实验跟踪、指标、artifact 和模型版本 | 第二阶段实验登记和模型对比工具候选 | 不替代 PostgreSQL `task_runs` / `task_artifacts` 审计账本 |
| [Optuna](https://optuna.org/) | 参数搜索和优化 | 第二阶段 lookback、holding period、分组数、交易参数优化 | 只能在受控研究任务中执行 |
| [Evidently](https://www.evidentlyai.com/) | 数据质量、漂移和模型表现监控 | 第二/三阶段因子分布漂移和上线后衰减监控 | 不直接决定生产准入 |

---

## 4. 当前已落地能力

### 4.1 公共协议

当前 `quant_contracts` 已包含：

```text
AssetClass
FactorMode
FactorFamily
EvaluationEngine
FactorCalculationRequest
FactorDailyValue
FactorCalculationMeta
FactorCalculationResponse
FactorValidationRequest
FactorValidationMetric
FactorValidationReport
FactorValidationFinding
FactorValidationManifest
FactorValidationResponse
FactorEvaluationResult
FactorScoreCard
FactorComparisonReport
TaskRun
TaskArtifact
```

后续需要扩展：

```text
ResearchReview
ForwardPerformance
MarketRegimeTag
DataQualitySnapshot
EvaluationEngineResult
```

### 4.2 因子计算

当前只实现动量类因子：

```text
momentum_*d = close_price / close_price.shift(N) - 1
```

已处理边界：

- 样本窗口不足时，`factor_value = null`。
- 前 N 日收盘价为空时，`factor_value = null`。
- 前 N 日收盘价为 0 时，`factor_value = null`。
- 计算按 `symbol + trade_date` 排序。
- 计算 T 日因子时只使用 T 日及以前的数据。

尚未实现：

```text
reversal_5d
volatility_20d
volume_ratio_20d
price_volume_corr_20d
行业/市值中性化
去极值
标准化
缺失值填充策略
期货连续合约和换月规则
期货期限结构因子
```

### 4.3 因子验证

当前 `quant_factor_validation` 已支持：

```text
forward_return_n
按交易日横截面计算 IC
按交易日横截面计算 Rank IC
IC mean
Rank IC mean
IC std
ICIR
按交易日横截面分组收益
高低分组收益差均值
coverage_ratio
missing_ratio
report.decision
report.findings
report.recommended_actions
manifest.task_run
manifest.artifacts
artifact file_size_bytes
artifact metadata.content_type
artifact metadata.sha256
manifest.persistence_status
evaluation_result
score_card.final_score
score_card.score_components
comparison_report.engine_count
comparison_report.has_engine_disagreement
```

当前 `report.decision` 只作为研究审核辅助状态，不等同于生产准入结论：

```text
insufficient_data
review_required
candidate_pass
candidate_reject
```

### 4.4 产物持久化

当前默认 `manifest.persistence_status = not_persisted`，接口会给出任务血缘、产物路径、JSON payload 大小和 sha256，但默认不会写入 PostgreSQL、MinIO 或其他生产存储。

当前代码已经具备：

```text
ValidationPersistenceService
MinIO / S3 object store adapter
SQLAlchemy 2.0 async PostgreSQL ledger repository
task_runs / task_artifacts schema
MinIO + PostgreSQL persistence smoke tool
score_card.json artifact
comparison_report.json artifact
101 节点 zeta_quant_factor_validation schema persisted smoke 通过
quant_ops_api 真实 task/artifact 只读账本读取通过
```

持久化开启前必须完成：

```text
对象存储配置
VALIDATION_DATABASE_URL
VALIDATION_DATABASE_SCHEMA，复用旧库时必须配置
task_runs / task_artifacts 表结构
生产或 101 节点密钥注入
make smoke-quant-factor-validation-persistence 端到端通过
```

### 4.5 Web UI

当前 `quant_ops_web` 已提供：

```text
Overview
Factor Validation review
Artifacts ledger preview
First-stage score preview
```

现阶段 Artifacts 页面默认展示 manifest preview；`quant_ops_api` 已支持 PostgreSQL `task_runs` / `task_artifacts` 只读账本读取路径，配置 `ARTIFACT_LEDGER_DATABASE_URL` 或 `VALIDATION_DATABASE_URL` 后可切换到真实账本。复用 101 旧库时需要同时配置 `ARTIFACT_LEDGER_DATABASE_SCHEMA=zeta_quant_factor_validation` 或 `VALIDATION_DATABASE_SCHEMA=zeta_quant_factor_validation`。

---

## 5. 三阶段评分路线

### 5.1 第一阶段：统一协议 + 多引擎对比 + 规则评分

目标：先让不同库和自研验证结果可比，而不是一开始训练自动判断模型。

本阶段当前已经落地：

```text
FactorEvaluationResult
FactorScoreCard
FactorComparisonReport
EvaluationEngine
score_components
final_score
review_decision
```

当前可运行引擎只有 `internal`。Alphalens、Qlib、vectorbt、OpenSourceAP/CrossSection 和 commodity-curve-factors 只作为后续 adapter / benchmark 的 `EvaluationEngine` 入口预留，尚未引入运行依赖。

建议评分先使用透明规则：

```text
final_score =
  rank_ic_ir_score
  + group_return_score
  + stability_score
  + turnover_penalty
  + coverage_score
  + drawdown_penalty
```

可接入或对照：

| 场景 | 对照引擎 |
| ---- | ---- |
| 股票截面因子 | internal validation、Alphalens、Qlib |
| 股票资产定价特征 | internal validation、OpenSourceAP/CrossSection |
| 股票 ML alpha | Qlib、internal validation |
| 期货时序因子 | vectorbt、internal backtest |
| 期货截面/期限结构 | commodity-curve-factors、internal validation |

第一阶段结论必须可解释。研究员应能看到每个 score component，而不是只看到一个黑盒分数。

### 5.2 第二阶段：实验沉淀 + 审核记录 + 后验表现

目标：积累 meta model 未来需要学习的数据，但仍不直接让模型决定生产准入。

本阶段需要沉淀：

```text
ExperimentRun
EvaluationEngineResult
FactorScoreCard
ResearchReview
ForwardPerformance
MarketRegimeTag
DataQualitySnapshot
```

建议工具：

| 能力 | 工具候选 | 使用方式 |
| ---- | ---- | ---- |
| 实验跟踪 | MLflow | 记录参数、指标、artifact、模型版本 |
| 参数搜索 | Optuna | 搜索 lookback、holding period、分组数、交易成本假设 |
| 漂移监控 | Evidently | 监控因子分布、覆盖率、数据质量和上线后衰减 |
| 任务审计 | PostgreSQL + MinIO | 继续作为生产审计账本和产物存储 |

第二阶段的关键不是“更复杂的模型”，而是把研究员审核、规则评分和后验表现放进同一个可追溯账本。

### 5.3 第三阶段：Meta Model / Ranking Model

目标：在有足够历史实验、研究员审核和后验表现后，训练模型辅助判断因子质量。

模型输入可以包括：

```text
IC / Rank IC 序列特征
分组收益稳定性
多空收益和回撤
换手率和交易成本敏感性
覆盖率和缺失率
不同 market regime 下表现
不同 evaluation_engine 的结果差异
研究员审核标签
上线后 forward_performance
```

模型输出可以包括：

```text
factor_quality_score
candidate_pass_probability
expected_decay_risk
recommended_weight
review_priority
```

可选实现：

```text
Qlib model workflow
LightGBM / scikit-learn ranking model
自研 scoring service
MLflow model registry
Evidently drift report
```

强约束：

- Meta model 只能作为辅助判断，不能替代研究员审核。
- 训练标签必须来自已审计的历史实验、后验表现和审核结果。
- 模型输入必须来自标准协议，不允许直接读取各库的私有结果格式。
- 生产准入仍需要明确的 `review_decision`、`reviewer_notes`、`approved_by` 和审计记录。

---

## 6. 研究员需要确认的问题

建议研究员优先确认：

1. 股票动量类因子默认使用 `raw`、`qfq` 还是 `hfq` 价格。
2. 股票截面因子是否需要统一股票池，例如全 A、沪深 300、中证 500。
3. 股票因子是否在计算阶段做去极值、标准化、中性化，还是在验证阶段处理。
4. 停牌、涨跌停、成交额过低、ST 股票是否进入第一版过滤规则。
5. 期货时序量价因子是否先从 TSMOM、突破、均线和波动率状态开始。
6. 期货连续合约、主力合约、换月和 roll rule 由哪个服务定义。
7. 期货截面因子是否优先做 carry、期限结构 slope/curvature 和 XSMOM。
8. 多引擎对比时，Alphalens、Qlib、vectorbt、自研结果冲突时由谁作为最终复核标准。
9. 第一阶段规则评分中，各 score component 的权重是否需要研究员确认。
10. `candidate_pass` 是否需要触发单独的生产准入流程。

---

## 7. 下一步建议

下一步不要直接扩展大量因子，建议按以下顺序推进：

```text
1. 为股票截面因子补充 Alphalens / Qlib 对照输出映射。
2. 为期货时序因子设计 vectorbt 或 internal backtest adapter。
3. 为期货期限结构因子整理 continuous contract、roll rule、carry、slope、curvature 协议。
4. 在 Web UI 接入真实多引擎对比、规则评分和研究员审核记录。
7. 沉淀 ResearchReview / ForwardPerformance / MarketRegimeTag / DataQualitySnapshot。
```

这样可以形成稳定闭环：

```text
因子计算
  ↓
多引擎验证
  ↓
规则评分
  ↓
研究员审核
  ↓
持久化账本
  ↓
后验表现沉淀
  ↓
Meta model 辅助判断
```
