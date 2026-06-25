# Apps / 应用

`apps/` 保存面向研究员、运维和管理视角的用户界面。应用层只做展示、编排和受控操作，不承载底层业务计算。

## 当前规划

```text
quant_ops_web/  # 运营 Dashboard / Monitoring UI，当前已落地 Overview 页面
```

## 本地入口

`quant_ops_web` 使用 React、TypeScript 和 Vite，通过 `/ops-api` 代理读取 `quant_ops_api`。

```bash
make quant-ops-web-up
make quant-ops-web-check
```

默认访问地址：

```text
http://127.0.0.1:18040
```

## 约束

- 应用不能直接 import 服务内部代码。
- 应用默认只读，写操作必须通过后端 API 和审计。
- 应用不能保存真实密钥或大规模数据。
- 展示数据必须来自 API、只读视图或标准 artifact manifest。
