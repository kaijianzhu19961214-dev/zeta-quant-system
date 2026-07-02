# quant_factor_lab / 因子计算服务

`quant_factor_lab` 负责因子定义、因子计算和因子产物生成。第一版只依赖 `quant_data_hub` 的标准行情接口，允许受控兼容第三方原始数据读取。

`quant_factor_lab` calculates factors and produces factor artifacts. The MVP should use `quant_data_hub` as the default data source while allowing controlled third-party raw-data adapters.

## 职责 / Responsibilities

- 定义因子输入、参数、窗口、频率和输出 schema。
- 调用 `quant_data_hub` 或 `quant_data_sdk` 获取标准行情数据。
- 生成因子值、因子元数据和计算产物 manifest。
- 将因子产物交给 MinIO 或后续统一 artifact 存储。

## 当前 MVP / Current MVP

当前已落地最小 FastAPI 服务：

```text
GET  /health
GET  /api/v1/algorithms
POST /api/v1/algorithms/review-gates/evidence/preview
POST /api/v1/algorithms/review-gates/evidence
GET  /api/v1/algorithms/{algorithm_id}/review-gates/evidence
POST /api/v1/algorithms/review-gates/evidence/{evidence_id}/review
GET  /api/v1/algorithms/{algorithm_id}/promotion/readiness
POST /api/v1/factors/calculate
```

第一批只实现：

```text
momentum_*d = close_price / close_price.shift(N) - 1
```

同时已建立第一阶段算法适配层：

```text
AlgorithmSpec
AlgorithmReviewGate
AlgorithmReviewGateEvidenceSubmission
AlgorithmReviewGateEvidenceRecord
FactorAlgorithmAdapter
FactorAlgorithmRegistry
```

当前 registry 中：

| algorithm_id | 状态 | 用途 |
| ---- | ---- | ---- |
| `technical.momentum` | `available` | 现有 momentum 因子计算 adapter |
| `volatility.egarch` | `planned` | EGARCH 波动率和杠杆效应候选算法 |
| `volatility.gjr_garch` | `planned` | GJR-GARCH 非对称波动候选算法 |
| `volatility.aparch` | `planned` | APARCH 非对称幂 ARCH 候选算法 |

每个算法会携带 `review_gates`，用于展示从 `planned` 升级到 `available` 前需要满足的门槛。`available` 算法不能存在 required 且 `missing` 的 gate；`planned` 算法只进入清单和研究审核，不会被执行。后续确认输入、参数、诊断指标、验证证据和 `arch` 依赖后，再补具体 adapter。

`POST /api/v1/algorithms/review-gates/evidence/preview` 用于校验研究员提交的 gate evidence，并返回标准 `AlgorithmReviewGateEvidenceRecord`；该接口不持久化。`POST /api/v1/algorithms/review-gates/evidence` 会写入 PostgreSQL `algorithm_review_gate_evidence` 表。`POST /api/v1/algorithms/review-gates/evidence/{evidence_id}/review` 用于将证据显式标记为 `accepted` 或 `rejected`，但不会自动修改 gate 状态。`GET /api/v1/algorithms/{algorithm_id}/promotion/readiness` 会只读合并 registry gate 状态和已审核证据，返回 `promotable` / `blocked`、required gate 完成数和阻塞原因。

示例：

```bash
curl -sS http://127.0.0.1:18010/health
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/algorithms
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/algorithms/review-gates/evidence/preview \
  -H 'content-type: application/json' \
  -d '{
    "algorithm_id": "volatility.egarch",
    "gate_id": "validation_evidence",
    "submitted_by": "researcher_a",
    "evidence_type": "validation_report",
    "evidence_source": "factor_validation/egarch_20d/comparison_report.json",
    "summary": "Rank IC, decay, turnover and cost sensitivity evidence for EGARCH.",
    "artifact_id": "egarch_20d_comparison_report"
  }'
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/algorithms/review-gates/evidence \
  -H 'content-type: application/json' \
  -d '{
    "algorithm_id": "technical.momentum",
    "gate_id": "validation_evidence",
    "submitted_by": "codex_smoke",
    "evidence_type": "validation_report",
    "evidence_source": "factor_validation/momentum_1d/comparison_report.json",
    "summary": "Momentum validation smoke evidence from 101 data.",
    "artifact_id": "comparison_report_momentum_1d"
  }'
```

```bash
curl -sS 'http://127.0.0.1:18010/api/v1/algorithms/technical.momentum/review-gates/evidence?gate_id=validation_evidence'
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/algorithms/review-gates/evidence/algorithm_gate_evidence_abc123/review \
  -H 'content-type: application/json' \
  -d '{
    "reviewed_by": "researcher_lead",
    "evidence_status": "accepted",
    "review_comment": "Validation evidence accepted for smoke verification."
  }'
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/algorithms/technical.momentum/promotion/readiness
```

```bash
curl -sS http://127.0.0.1:18010/api/v1/factors/calculate \
  -H 'content-type: application/json' \
  -d '{
    "factor_name": "momentum_20d",
    "symbols": ["000001.SZ"],
    "start": "2026-01-01",
    "end": "2026-03-13",
    "lookback_window": 20
  }'
```

运行测试：

```bash
make test-quant-factor-lab
```

启动容器：

```bash
make quant-factor-lab-up
make quant-factor-lab-check
```

## 第三方原始数据兼容 / Third-Party Raw Data Compatibility

允许兼容读取第三方原始数据，但必须满足：

- 只能通过明确的 adapter 接入，不能在因子代码中散落第三方 API 调用。
- adapter 输出必须转换为 `quant_contracts` 的标准模型。
- 读取过程必须记录 source、version、time_range、field_mapping 和 license 约束。
- 生产默认路径仍应优先走 `quant_data_hub`，避免因子服务变成第二套数据接入系统。

## 不做什么 / Non-Goals

- 不负责长期保存原始行情数据。
- 不绕过数据协议直接写入 ClickHouse。
- 不承担因子有效性统计和报告生成；这部分属于 `quant_factor_validation`。
