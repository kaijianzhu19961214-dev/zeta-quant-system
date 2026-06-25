# quant_factor_validation / 因子验证服务

`quant_factor_validation` 负责对因子产物进行统计检验、分组回测式验证和报告生成。

`quant_factor_validation` validates factor artifacts and produces research reports.

## 职责 / Responsibilities

- 读取因子产物、行情收益和股票池定义。
- 计算 IC、Rank IC、分组收益、换手、覆盖率、缺失率和稳定性指标。
- 输出结构化验证结果和可复现报告。
- 记录验证任务、参数、输入产物、输出产物和代码版本。

## 输入 / Inputs

```text
factor artifact
market return data
universe definition
calendar
validation config
```

## 输出 / Outputs

```text
metrics tables
figures
markdown / html / pdf reports
artifact manifest
```

## 约束 / Rules

- 验证逻辑必须可复现：同一输入、同一配置、同一代码版本应得到一致结果。
- 指标模型和报告摘要字段必须复用 `quant_contracts`。
- 第一版先做离线验证；在线服务化接口在 MVP 稳定后再补。

