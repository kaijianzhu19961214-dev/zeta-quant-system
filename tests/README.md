# Tests / 测试

`tests/` 保存跨包、跨服务的集成测试和系统级验证说明。单个包或服务的单元测试优先放在对应目录内。

`tests/` stores cross-package and cross-service validation. Unit tests should live near each package or service.

## 测试分层 / Test Layers

```text
unit:
  no real external services, use unittest and fixtures

integration:
  local containers, small fixtures, no real secrets

remote smoke:
  manually triggered read-only or dry-run checks against 101
```

## 约束 / Rules

- Python 测试框架使用 `unittest`。
- 默认测试不能依赖 101 节点、真实数据或真实密钥。
- 需要远程数据的测试必须显式命名为 smoke test，并在文档中说明只读或 dry-run。
- fixture 必须小型、可公开、无敏感信息。

