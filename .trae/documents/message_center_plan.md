# 消息中心功能开发计划

## 1. 目标
搭建一个消息中心页面，支持查看、搜索、过滤各个 Channel 的消息，并提供 AI 总结功能（针对选中消息或查询结果）。

## 2. 现状分析
- **后端**：
    - 已有 `Channel` 和 `ChannelMessage` 模型。
    - `ChannelService` 提供了 `get_channel_messages` 方法，但仅支持 `channel_id` 过滤，缺乏全局搜索、时间范围过滤等功能。
    - 已有 `ChatService` 提供 AI 对话能力。
- **前端**：
    - 已有 `/channels` 页面进行渠道管理。
    - 缺乏统一的消息查看和操作界面。

## 3. 实施步骤

### 第一阶段：后端 API 开发
1.  **修改 `ChannelService` (`backend/app/services/channel_service.py`)**：
    - 新增 `get_messages` 方法，支持以下参数：
        - `channel_id` (可选，过滤特定渠道)
        - `keyword` (可选，搜索消息内容)
        - `start_date`, `end_date` (可选，时间范围)
        - `status` (可选，发送状态)
        - `skip`, `limit` (分页)
    - 返回包含 `items` (消息列表) 和 `total` (总数) 的字典或对象。

2.  **修改 Channel Router (`backend/app/api/channel.py`)**：
    - 新增接口 `GET /messages`，调用 `ChannelService.get_messages`。
    - 定义请求参数和响应模型。

### 第二阶段：前端页面开发
1.  **封装 API (`frontend/packages/web/src/api/message.js`)**：
    - 封装 `getMessages` 方法，调用后端新接口。
2.  **开发消息中心页面 (`frontend/packages/web/src/pages/message/index.vue`)**：
    - **布局**：
        - 顶部筛选栏：渠道选择器、时间范围选择器、关键词搜索框、搜索按钮。
        - 操作栏：
            - "选中消息 AI 总结" 按钮（禁用状态控制：仅当有选中项时可用）。
            - "查询结果 AI 总结" 按钮（对当前过滤条件下的消息进行总结）。
        - 消息列表（Table）：
            - 列：选择框、时间、渠道、内容（截断展示）、状态、结果、操作（查看详情）。
            - 分页组件。
    - **交互逻辑**：
        - 加载渠道列表用于筛选。
        - 调用 `getMessages` 获取数据。
        - 详情弹窗：展示完整消息内容和发送结果。
3.  **开发 AI 总结功能**：
    - **总结弹窗组件**：
        - 用于展示 AI 总结的流式输出。
    - **选中总结逻辑**：
        - 获取选中行的消息内容。
        - 拼接 Prompt："请总结以下消息：\n[消息内容列表]"。
        - 调用 `ChatService` 创建会话并发送 Prompt，流式展示结果。
    - **查询结果总结逻辑**：
        - 获取当前筛选条件下的前 N 条消息（例如最近 50 条）。
        - 拼接 Prompt，进行总结。

### 第三阶段：路由与入口配置
1.  **配置路由 (`frontend/packages/web/src/router.js`)**：
    - 添加 `/messages` 路由，指向消息中心页面。
2.  **添加入口 (`frontend/packages/web/src/App.vue`)**：
    - 在导航栏添加 "消息中心" 链接。

## 4. 验证计划
1.  **后端验证**：使用 Swagger UI 测试 `GET /api/v1/channels/messages` 接口，验证筛选和分页功能。
2.  **前端验证**：
    - 进入消息中心，验证列表加载。
    - 测试按渠道、时间、关键词筛选。
    - 选中多条消息，点击 "AI 总结"，验证 AI 回复是否准确。
    - 验证详情查看功能。
