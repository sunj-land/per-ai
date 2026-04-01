# 基于 Nanobot Channel 实现多平台 Bot 消息推送服务 - 实施计划

## 1. 概述
本计划旨在后端服务中复刻 **Nanobot Channel** 核心能力，实现统一的消息推送服务。该服务将支持多平台 Bot（钉钉、企业微信、飞书等）的适配与消息分发，作为系统内部的消息总线，供任务中心、RSS 订阅或 Agent 使用。

## 2. 核心架构

### 2.1 整体流程
`消息生产者 (API/Task/Agent)` -> `Channel Service (业务逻辑)` -> `Channel Manager (适配器管理)` -> `Platform Adapter (钉钉/飞书/企微)` -> `第三方平台 API`

### 2.2 数据模型 (SQLModel)
*   **Channel**: 存储通道配置信息。
    *   `id`: UUID
    *   `name`: 通道名称 (e.g., "运维告警群")
    *   `type`: 平台类型 (dingtalk, feishu, wechat_work, slack, email, webhook)
    *   `config`: JSON 字段，存储 Webhook URL, Secret, Token 等敏感信息
    *   `description`: 描述
    *   `status`: 启用/禁用状态
    *   `created_at`, `updated_at`
*   **ChannelMessage**: 存储消息发送记录（可选，用于审计和重试）。
    *   `id`: UUID
    *   `channel_id`: 关联通道
    *   `content`: 发送内容 (JSON/Text)
    *   `status`: pending, success, failed
    *   `result`: 第三方接口返回的响应
    *   `created_at`

### 2.3 核心模块设计 (`backend/app/core/channel/`)
*   **BaseAdapter**: 定义适配器接口（`send_text`, `send_markdown`, `validate_config`）。
*   **AdapterFactory**: 根据 Channel 类型实例化对应的 Adapter。
*   **Adapters**:
    *   `DingTalkAdapter`: 钉钉机器人 (Webhook + 加签/关键词)
    *   `FeishuAdapter`: 飞书机器人 (Webhook + 签名校验)
    *   `WecomAdapter`: 企业微信机器人
*   **ChannelManager**: 负责加载配置、初始化适配器、执行发送逻辑。

## 3. 实施步骤

### 阶段一：基础框架与模型 (MVP)
1.  **创建数据模型**：
    *   新建 `backend/app/models/channel.py` 定义 `Channel` 和 `ChannelMessage`。
    *   新建 `backend/app/schemas/channel.py` 定义 Pydantic 模型 (Create/Update/Response)。
    *   在 `backend/app/models/__init__.py` 中注册新模型。
    *   生成并执行 Alembic 迁移脚本。

2.  **实现核心适配器逻辑**：
    *   新建 `backend/app/core/channel/base.py` 定义基类。
    *   新建 `backend/app/core/channel/dingtalk.py` 实现钉钉适配器（优先实现）。
    *   新建 `backend/app/core/channel/factory.py` 实现工厂模式。

3.  **实现业务服务层**：
    *   新建 `backend/app/services/channel_service.py`，处理 CRUD 和 `send_message` 逻辑。

4.  **实现 API 接口**：
    *   新建 `backend/app/api/v1/endpoints/channels.py`。
    *   提供 `POST /channels` (创建), `GET /channels` (列表), `POST /channels/{id}/send` (测试发送), `POST /channels/broadcast` (广播)。
    *   在 `backend/app/api/v1/api.py` 中注册路由。

### 阶段二：多平台适配与增强 (后续迭代)
1.  **增加适配器**：
    *   实现 `FeishuAdapter` (飞书)。
    *   实现 `WecomAdapter` (企业微信)。
2.  **集成任务系统**：
    *   在 `TaskService` 中支持 `channel` 类型的任务，允许定时触发消息推送。

## 4. 验证计划
1.  **单元测试**：测试 Adapter 的参数封装逻辑。
2.  **接口测试**：
    *   创建钉钉机器人通道。
    *   调用 `POST /send` 接口发送文本消息。
    *   验证钉钉群是否收到消息。
    *   验证数据库中 `ChannelMessage` 是否记录成功。

## 5. 依赖检查
*   需要 `httpx` 或 `requests` 库用于发送 HTTP 请求（项目中已有 `httpx`）。
*   需要 `SQLModel` 和 `PostgreSQL` 环境（项目中已有）。
