# 因子处理与审核流程现状说明

> 面向对象：量化研究员。本文只展示当前项目中已经落地或已经明确约束的因子处理流程，便于判断还需要补充哪些研究、验证和风控要求。

---

## 1. 当前因子主链路

当前 MVP 主链路是：

```text
quant_data_hub
  ↓ 标准行情数据
quant_data_sdk
  ↓ Python 客户端
quant_factor_lab
  ↓ 因子值
quant_factor_validation
  ↓ IC / Rank IC 验证摘要与候选审核状态
```

当前因子计算服务不直接读取 101 节点数据库，也不直接调用第三方数据源。所有行情输入默认来自 `quant_data_hub` 的标准行情接口。

---

## 2. 已有因子协议

当前公共协议已经定义在 `quant_contracts` 中，核心对象包括：

```text
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
```

研究员需要关注的输入字段：

| 字段 | 说明 |
| ---- | ---- |
| `factor_name` | 因子名称，例如 `momentum_20d` |
| `symbols` | 股票列表 |
| `start` / `end` | 样本区间 |
| `timeframe` | 当前 MVP 只支持 `1d` |
| `price_mode` | `raw` / `qfq` / `hfq`，当前可传入协议层 |
| `batch_id` | 使用 `qfq` 时必须指定 |
| `lookback_window` | 回看窗口，必须和因子名中的窗口一致 |
| `run_id` | 运行批次，用于审计和复现 |
| `data_source` | 默认 `quant_data_hub` |
| `data_version` | 数据版本，可选 |
| `factor_version` | 因子版本，默认 `v1` |

输出的因子值包含：

```text
symbol
trade_date
factor_name
factor_value
universe_name
data_source
data_version
factor_version
run_id
```

---

## 3. 已实现因子

当前只实现了动量类因子：

```text
momentum_*d = close_price / close_price.shift(N) - 1
```

例如：

```text
momentum_20d = close_price_t / close_price_t-20 - 1
```

已处理的边界情况：

- 样本窗口不足时，`factor_value = null`。
- 前 N 日收盘价为空时，`factor_value = null`。
- 前 N 日收盘价为 0 时，`factor_value = null`。
- 计算按 `symbol + trade_date` 排序。
- 计算 T 日因子时只使用 T 日及以前的数据。

当前尚未实现：

```text
reversal_5d
volatility_20d
volume_ratio_20d
price_volume_corr_20d
行业/市值中性化
去极值
标准化
缺失值填充策略
```

---

## 4. 当前审核约束

当前项目已经明确以下审核约束：

- 因子计算函数尽量保持纯函数。
- 不允许在因子函数中直接调用第三方 API。
- 不允许在因子函数中隐式读取当前日期、数据库最新值或外部状态。
- 第三方原始数据如果要兼容，必须先通过 adapter 转成标准模型。
- 因子结果必须保留 `run_id`、`data_source`、`data_version`、`factor_version`。
- 使用 `qfq` 价格口径时必须指定 `batch_id`。
- 当前 MVP 因子只支持日频数据。
- 任何新增因子必须有固定样本的确定性单元测试。

---

## 5. 已有测试覆盖

当前已经覆盖：

```text
因子请求字段校验
qfq batch_id 校验
momentum 计算正确性
窗口不足返回 null
前序价格为 0 返回 null
FastAPI 路由成功响应
不支持的因子返回参数错误
quant_factor_lab 通过 quant_data_sdk 读取标准行情
```

当前测试重点是确定性和边界条件，还没有覆盖真实大样本统计稳定性。

当前 `quant_factor_validation` MVP 已支持：

```text
forward_return_n
按交易日横截面计算 IC
按交易日横截面计算 Rank IC
IC mean
Rank IC mean
IC std
ICIR
coverage_ratio
missing_ratio
report.decision
report.findings
report.recommended_actions
manifest.task_run
manifest.artifacts
manifest.persistence_status
```

当前 `report.decision` 只作为研究审核辅助状态，不等同于生产准入结论：

```text
insufficient_data
review_required
candidate_pass
candidate_reject
```

当前 `manifest.persistence_status = not_persisted`，表示接口已经给出任务血缘和产物路径预览，但还没有写入 PostgreSQL、MinIO 或其他生产存储。

当前 `quant_ops_web` 已提供 Factor Validation 只读展示页：

```text
decision
effective_sample_count / sample_count
coverage_ratio
IC / Rank IC
report.findings
report.recommended_actions
manifest.artifacts
manifest.persistence_status
```

该页面通过 `quant_ops_api /api/v1/factor-validation/review` 读取审核摘要。现阶段展示的是 MVP manifest preview，后续应接入 PostgreSQL `task_runs` / `task_artifacts` 或 MinIO `latest.json` 后再作为正式审核账本。

---

## 6. 研究员建议重点确认

建议研究员优先判断以下问题：

1. `momentum_20d` 是否应使用 `raw`、`qfq` 还是 `hfq` 价格作为默认口径？
2. 窗口不足时返回 `null` 是否符合后续验证流程？
3. 是否需要在因子层做停牌、涨跌停、成交额过低、ST 股票过滤？
4. 是否需要统一股票池定义，例如全 A、沪深 300、中证 500？
5. 因子值是否需要在计算阶段就做去极值、标准化、中性化？
6. `run_id`、`data_version`、`factor_version` 是否满足研究复现要求？
7. 第一批因子的优先级是否仍然是：动量、反转、波动率、量比、价量相关？
8. 因子审核通过后，Web UI 中的 `candidate_pass` 是否需要触发单独的生产准入流程？

---

## 7. 下一步建议

建议下一步不要直接扩展大量因子，而是先补齐：

```text
quant_factor_validation manifest 持久化与分组收益
FactorDailyValue 的持久化或 artifact 输出规范
固定样本验证报告
研究员确认后的因子审核清单
Web UI 中的因子运行列表、正式验证报告列表和产物链接
```

这样可以先形成：

```text
因子计算 → 因子验证 → 审核意见 → 是否进入下一阶段
```

的闭环。
