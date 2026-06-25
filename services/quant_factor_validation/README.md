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

## 当前 MVP / Current MVP

当前已落地最小 FastAPI 服务：

```text
GET  /health
POST /api/v1/factors/validate
```

第一批只计算：

```text
forward_return_n
IC
Rank IC
IC mean
Rank IC mean
IC std
ICIR
coverage_ratio
missing_ratio
```

示例：

```bash
curl -sS http://127.0.0.1:18020/health
```

```bash
curl -sS http://127.0.0.1:18020/api/v1/factors/validate \
  -H 'content-type: application/json' \
  -d '{
    "factor_name": "momentum_1d",
    "factor_values": [
      {
        "symbol": "000001.SZ",
        "trade_date": "2026-03-13",
        "factor_name": "momentum_1d",
        "factor_value": "0.1"
      }
    ],
    "market_start": "2026-03-13",
    "market_end": "2026-03-16",
    "forward_days": 1
  }'
```

运行测试：

```bash
make test-quant-factor-validation
```

启动容器：

```bash
make quant-factor-validation-up
make quant-factor-validation-check
```

## 约束 / Rules

- 验证逻辑必须可复现：同一输入、同一配置、同一代码版本应得到一致结果。
- 指标模型和报告摘要字段必须复用 `quant_contracts`。
- 当前在线接口只做只读验证计算，不保存报告、不写生产表。
