# 代码 Review 发现与处理计划

更新时间：2026-06-23

本文记录当前 `quant-data-ingestion-layer` 已实现代码的 review 结论，用于跟踪哪些问题已经修复，哪些需要在生产化前继续处理。

## 1. 当前结论

已处理：

- SDK 文件上传/下载从一次性读入内存改为流式传输。
- `task_runs` 状态更新不再误清空未传入的 `output_summary` 和 `error_message`。
- 已限制终态任务回退，例如 `succeeded` 不能再改回 `running`。
- `task_artifacts` 的 `artifact_type` 过滤已经下推到 SQL。
- 任务查询类接口已经改用读库 session，为后续读写分离预留路径。
- `register_task_artifact` 已将同步 MinIO 元信息读取放入线程池，避免阻塞事件循环。
- MinIO bucket 默认值、Swagger 描述和文档口径已经统一为 `quant-factor-data`。

仍待处理：

- API token 鉴权还没有落地。
- MinIO SDK 大文件上传已经避免一次性读内存，但仍需在真实大文件和预签名 URL 下做压力验证。
- `MinioStorageClient.ensure_bucket_exists()` 当前会在读/写路径自动创建 bucket，生产环境建议改为启动检查或运维初始化。
- 任务和 artifact 接口还缺少数据库级集成测试。

## 2. Findings

### [已修复] SDK 大文件上传/下载内存风险

位置：

```text
quant_data_sdk/client.py
```

原问题：

```text
put_file 使用 path.read_bytes()
download_file 使用 response.read()
```

影响：

大 parquet、CSV 或回测产物会被一次性读入内存，研究员上传/下载较大文件时可能触发 OOM。

处理结果：

- 上传使用本地文件对象流式传给 `urllib.request.urlopen`。
- 上传显式设置 `Content-Length`，避免预签名 PUT URL 因 chunked 传输不兼容。
- 下载使用 `.part` 临时文件和 `shutil.copyfileobj` 分块写入，完成后原子替换目标文件。

### [已修复] 任务状态更新会误清空摘要或错误信息

位置：

```text
app/services/task_service.py
```

原问题：

`TaskStatusUpdateRequest` 中未传入的 `output_summary` / `error_message` 会被写成 `None`。

影响：

后续状态更新可能清空研究任务已有的指标摘要或错误原因。

处理结果：

- 使用 `request.model_fields_set` 判断字段是否真的传入。
- 未传入时保留原值。
- 显式传 `null` 时允许清空。

### [已修复] 终态任务可以被误改回运行中

位置：

```text
app/services/task_service.py
app/api/v1/tasks.py
```

原问题：

`succeeded`、`failed`、`cancelled` 等终态任务可以再次被改成 `running`。

影响：

任务账本会出现不一致状态，影响研究结果追溯。

处理结果：

- 增加 `InvalidTaskStatusTransitionError`。
- 终态任务只允许重复写同一终态，用于补充摘要；不允许回退到非终态。
- API 对非法状态转换返回 `409 Conflict`。

### [已修复] `task_artifacts` 类型过滤发生在内存中

位置：

```text
app/api/v1/tasks.py
app/services/task_service.py
app/repositories/task_repository.py
```

原问题：

接口先查询最近 N 条 artifact，再在 Python 内存中过滤 `artifact_type`。

影响：

当某个任务产物数量较多时，可能漏掉符合类型但不在最近 N 条中的结果。

处理结果：

`artifact_type` 已下推到 SQL 查询条件。

### [已修复] async route 中同步调用 MinIO SDK

位置：

```text
app/services/task_service.py
```

原问题：

`register_minio_artifact` 是 async 服务方法，但内部直接调用同步 `minio_client.stat_object`。

影响：

MinIO 延迟或网络抖动时会阻塞 FastAPI 事件循环，影响其他请求响应。

处理结果：

同步 MinIO 元信息读取已通过 `run_in_threadpool` 放入线程池执行。

## 3. 生产化前仍需处理

| 优先级 | 问题 | 影响 | 建议 |
|---|---|---|---|
| P0 | API token 鉴权未落地 | tasks/artifacts/presign URL 暴露风险 | 增加 Bearer token 依赖，先保护 `/api/v1/tasks` 和 `/api/v1/artifacts` |
| P1 | bucket 自动创建发生在读写路径 | `.env` 配错可能创建错误 bucket | 生产环境改成 fail closed，bucket 创建交给部署脚本 |
| P1 | 大文件真实压力验证未完成 | 仍需确认 101 和后续 7T 阵列传输稳定性 | 用 1GB、5GB parquet 做上传/下载和 checksum 验证 |
| P2 | 缺少 API 集成测试 | 路由、数据库、MinIO 组合路径覆盖不足 | 增加 unittest 集成测试，Mock MinIO 边界 |

## 4. 验证

本轮执行：

```bash
.venv/bin/python -m unittest discover -s tests
```

结果：

```text
35 tests OK
```
