# Channel 模块架构与开发文档

## 1. 模块的整体架构设计和职责边界
`backend/app/core/channel` 模块是本系统连接外部世界的桥梁，专门负责对接各种即时通讯软件和第三方平台。该模块采用了**高内聚、低耦合的可插拔式（Pluggable）架构**，将“如何发送消息”的底层细节与“发送什么内容”的上层业务逻辑彻底分离。

**职责边界**：
- **核心抽象 (`base.py`)**：定义所有渠道必须遵循的公共接口和生命周期（鉴权、发送文本、发送 Markdown、接收消息），并内建指标收集（请求成功率、延迟等）功能。
- **工厂模式 (`factory.py`)**：负责集中注册、管理和实例化具体的渠道适配器（Adapter），隐藏实例化的复杂性。
- **具体适配器实现**：每个渠道独立为一个 Python 文件（如 `dingtalk.py`, `qqbot.py`, `wechat_work.py`, `feishu.py`, `discord.py`, `slack.py`, `teams.py`, `email_adapter.py` 等）。它们继承自 `BaseAdapter`，封装特定平台 API 的请求逻辑、签名算法和回调解析。
- **业务胶水层 (`channel_service.py` 位于外部 `services` 目录)**：负责持久化渠道配置、提供对外 API（如 CRUD 和 Webhook 入口），并协调 `AdapterFactory` 完成实际的发送。

## 2. 核心组件的详细功能说明
- **`BaseAdapter` (基础适配器)**：
  - 定义了 `send_text`, `send_markdown`, `receive` 等核心异步方法。
  - 提供 `validate_config` 和 `authenticate` 方法以校验配置合法性。
  - 内置 `record_metric` 方法，用于统计每个渠道的健康状况（总请求数、成功/失败数、平均耗时）。
  - 新增 `set_channel_id` 方法，将通道唯一标识注入到适配器实例中，便于消息追踪。
- **`AdapterFactory` (适配器工厂)**：
  - 维护一个全局字典 `_adapters`，将渠道类型字符串（如 `"qqbot"`）映射到对应的类（如 `QQBotAdapter`）。
  - 提供 `create_adapter(channel_type, config)` 方法，实现按需加载与动态初始化。
- **`QQBotAdapter` (`qqbot.py`)**：
  - 基于腾讯 QQ 开放平台 v2 接口实现，支持群聊与 C2C 单聊消息发送。
  - 特有逻辑：当群聊发送失败（如禁言，错误码 11255）时，内置“自动降级至 C2C 私聊”的 Fallback 策略。
  - 依赖配置：`appId`, `secret`, `sandbox` 以及白名单 `allowFrom`。

## 3. 模块间的交互流程和数据流转
整个渠道发送流程采用统一标准，屏蔽了底层的异构性。
1. **配置加载**：系统从数据库（`Channel` 表）加载对应渠道的 JSON 配置。
2. **实例化适配器**：通过 `AdapterFactory.create_adapter()` 传入类型与配置，获得一个特定的适配器实例（如 DingTalkAdapter）。
3. **调用发送方法**：业务层统一调用 `adapter.send_text(content)`，将消息内容传递给适配器。
4. **底层网络交互**：适配器内部使用 `httpx` 或 `requests` 构建特定的 HTTP 请求（如 Webhook 签名、Bearer Token 等），向第三方服务器发起调用。
5. **结果返回与指标记录**：第三方服务器响应后，适配器解析结果并返回标准字典结构（如 `{"status": "success", "message_id": "xxx"}`），并在 `finally` 块中调用 `record_metric` 更新健康数据。
6. **Webhook 接收**：外部平台向系统的 `/api/v1/channels/{channel_id}/webhook` 发起请求时，系统提取 Payload 并交由对应适配器的 `receive()` 方法处理，将外部格式转换为内部的 `InboundMessage` 格式，最后投入事件总线。

## 4. 关键业务场景的处理流程
**场景一：新增一个自定义渠道（如 MyChat）**
1. **创建适配器**：在 `app/core/channel/mychat.py` 中继承 `BaseAdapter`。
2. **实现抽象方法**：重写 `send_text`, `send_markdown`, `validate_config` 等，封装 MyChat 的专属 API 请求。
3. **注册到工厂**：在 `factory.py` 中导入 `MyChatAdapter`，并将其加入 `_adapters` 字典。
4. **配置数据库**：通过前端或 API 在数据库中插入一条类型为 `mychat` 的渠道记录，填入对应的 `api_key`。

**场景二：QQBot 消息发送与失败降级**
1. 系统尝试向 QQ 群发送一条 Markdown 消息。
2. 腾讯 API 返回 `11255` 错误（表示群聊不可用或被禁言）。
3. `QQBotAdapter` 捕获异常，检查目标是否属于 `allowFrom` 白名单。
4. 若属于，则提取 OpenID，并向 C2C 接口重新发起请求，确保消息送达。

## 5. 配置参数说明和使用示例
渠道配置通常以 JSON 格式存储在数据库的 `channel.config` 字段中。

**QQBot 配置示例**：
```json
{
  "appId": "102030405",
  "secret": "your_client_secret_here",
  "sandbox": false,
  "allowFrom": ["openid_user1", "openid_user2"]
}
```

**钉钉 (DingTalk) 配置示例**：
```json
{
  "webhook_url": "https://oapi.dingtalk.com/robot/send?access_token=xxx",
  "secret": "SECxxxxxxxx"
}
```

**代码调用示例**：
```python
from app.core.channel.factory import AdapterFactory

# ========== 步骤1：从工厂获取适配器实例 ==========
adapter = AdapterFactory.create_adapter("dingtalk", {
    "webhook_url": "https://...",
    "secret": "SEC..."
})

# ========== 步骤2：执行发送逻辑并记录状态 ==========
if adapter.validate_config():
    result = await adapter.send_text("Hello World")
    print(f"发送状态: {result}")
```

## 6. 可能存在的性能瓶颈和优化建议
1. **同步网络阻塞 (Synchronous Blocking)**：
   - **瓶颈**：如果在某些适配器中（如早期的钉钉或微信实现）使用了同步的 `requests` 库，这会阻塞整个异步事件循环，导致其他协程被挂起。
   - **优化建议**：强制所有网络请求（特别是 Webhook 发送）使用 `httpx.AsyncClient` 进行异步非阻塞调用。
2. **频率限制与限流 (Rate Limiting)**：
   - **瓶颈**：各大开放平台（如 QQ、微信）均对 API 调用有严格的 QPS 限制。当系统在短时间内产生大量告警或消息时，极易触发 HTTP 429 Too Many Requests 错误，导致消息丢失。
   - **优化建议**：在 `ChannelService` 或各 `Adapter` 中引入令牌桶（Token Bucket）或漏桶（Leaky Bucket）限流算法；并在失败时结合重试队列（Exponential Backoff）进行延迟发送。
3. **内存泄漏与连接池耗尽**：
   - **瓶颈**：如果每个发送请求都实例化一个新的 `httpx.AsyncClient`，在高并发下会导致系统描述符耗尽。
   - **优化建议**：在 `BaseAdapter` 级别维护一个全局的、单例的 `httpx.AsyncClient` 连接池，供所有子类共享和复用。
