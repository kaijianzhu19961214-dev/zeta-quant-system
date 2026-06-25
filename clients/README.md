# Clients / 客户端

`clients/` 保存面向研究员、脚本和其他服务的客户端 SDK。客户端只封装协议和调用方式，不承担服务端业务逻辑。

`clients/` stores SDKs for researchers, scripts, and internal services.

## 当前客户端 / Current Client

```text
quant_data_sdk/  # Python SDK for quant_data_hub
```

## 约束 / Rules

- SDK 输入输出优先复用 `quant_contracts`。
- SDK 不能保存真实密钥，认证信息只能从调用方配置注入。
- SDK 不能把大规模数据默认下载到本机。
- SDK 错误消息应适合研究员定位问题，但不能打印 token、password、access key。

