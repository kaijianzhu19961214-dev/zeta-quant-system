# Python 运行时策略

> 目标：项目使用可复现的 Python 运行时，同时不破坏 macOS / Xcode 自带 Python。

---

## 1. 结论

本项目采用容器优先策略，MVP 服务镜像默认使用：

```text
python:3.12.13-slim
```

原因：

- Python 3.12 对量化常用依赖、FastAPI、Pydantic v2、SQLAlchemy 2.0、pandas、pyarrow 等生态更稳。
- Python 3.12 已进入 security 维护，适合作为第一版生产基线。
- Python 3.13 和 3.14 可作为后续兼容性验证目标。
- Python 3.9 已 end-of-life，不应作为新项目基线。

参考：

- [Python downloads](https://www.python.org/downloads/)
- [Python 3.12.13](https://www.python.org/downloads/release/python-31213/)
- [Python 3.14.6](https://www.python.org/downloads/release/python-3146/)

---

## 2. 不覆盖系统 Python

不要覆盖 macOS / Xcode 自带的 Python：

```text
/usr/bin/python3
/Applications/Xcode.app/.../python3
```

这些 Python 由系统或开发工具管理，强行替换容易影响系统脚本、Xcode 工具链和后续 macOS 更新。

正确做法是通过容器固定项目环境；如果本机需要运行单元测试，再并行安装项目 Python。

---

## 3. 容器优先

服务镜像固定小版本：

```dockerfile
FROM python:3.12.13-slim
```

本地容器测试：

```bash
make test-quant-contracts-container
```

这样 Mac 本机 Python 版本不会影响项目结果。

---

## 4. 项目虚拟环境约定

如果需要在 Mac 本机直接运行测试，项目根目录使用 `.python-version` 锁定与容器一致的版本：

```text
3.12.13
```

本地开发建议：

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install -U pip
python -m pip install -e packages/quant_contracts
```

验证：

```bash
make test-quant-contracts
```

如果已经在本机准备好 Python 3.12 环境，也可以运行：

```bash
make test-quant-contracts-local
```

---

## 5. 本机安装工具

当前这台 Mac 暂未检测到：

```text
brew
pyenv
uv
```

因此后续如果要真正安装本机 Python，建议先选择一个管理工具。为了避免污染系统环境，默认不自动安装 Homebrew 或替换系统 Python。

推荐优先级：

```text
1. uv 或 pyenv 管理项目 Python
2. Homebrew 安装 python@3.12
3. python.org 官方 pkg 安装器
```

---

## 6. 镜像约束

生产镜像必须显式固定 Python 小版本，不使用 `latest` tag，避免基础镜像漂移导致不可复现。
