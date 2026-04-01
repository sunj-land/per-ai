# Agents 服务迁移与接口化改造方案

## 1. 概述
本方案旨在将原根目录下的 `core` 和 `nodes` 模块迁移至独立的 `agents` 服务模块，实现大模型功能的集中管理与服务化。通过统一的 RESTful 接口对外提供服务，解耦后端业务与底层 AI 能力。

## 2. 新旧架构对比

| 特性 | 旧架构 (Direct Import) | 新架构 (Service Oriented) |
| :--- | :--- | :--- |
| **代码位置** | `root/core`, `root/nodes` | `agents/core`, `agents/nodes` |
| **调用方式** | Python 模块直接导入 | HTTP RESTful API 调用 |
| **依赖管理** | 混合在 backend 依赖中 | `agents` 独立依赖管理 |
| **扩展性** | 耦合度高，难以独立扩展 | 独立服务，支持水平扩展 |
| **容错性** | 异常直接影响主进程 | 支持熔断、重试、降级 |

## 3. 接口清单

所有接口统一在 `agents/api/service.py` 中定义，服务端口默认为 8001。

### 3.1 LLM 基础能力
- **Chat Completion**: `POST /api/v1/llm/chat`
  - 支持流式 (SSE/NDJSON) 和非流式响应
  - 统一封装 `litellm` 调用
- **Embedding**: `POST /api/v1/llm/embedding`

### 3.2 节点能力 (Nodes)
- **Text Generation**: `POST /api/v1/nodes/generate`
- **Text Classification**: `POST /api/v1/nodes/classify`
- **Text Summarization**: `POST /api/v1/nodes/summarize`

### 3.3 Agent 管理
- **List Agents**: `GET /api/v1/agents/list`
- **Get Agent Graph**: `GET /api/v1/agents/{agent_name}/graph`

## 4. 迁移步骤

1. **目录结构调整**
   - 移动 `core` -> `agents/core`
   - 移动 `nodes` -> `agents/nodes`
   - 建立 `agents/api` 目录

2. **服务层实现**
   - 创建 `agents/api/service.py` (FastAPI 应用)
   - 实现统一的请求/响应模型 (Pydantic Contracts)

3. **Backend 客户端适配**
   - 创建 `AgentsServiceSyncClient` (封装 HTTPX, Circuit Breaker, Rate Limiter)
   - 替换 `AIProviderFactory` 实现，接入 `AgentsProvider`
   - 替换 `AgentService` 中的直接引用

4. **依赖清理**
   - 删除根目录下的 `core` 和 `nodes`
   - 清理 backend 中对旧模块的引用

## 5. 回滚策略

若服务化改造出现严重问题，可按以下步骤回滚：
1. 恢复根目录下的 `core` 和 `nodes` 文件夹（从 Git 历史恢复）。
2. 将 `backend/app/core/ai_providers.py` 中的 `AgentsProvider` 替换回原有的本地调用实现。
3. 将 `backend/app/services/agent_service.py` 中的 `AgentsServiceSyncClient` 替换回直接导入。

## 6. 注意事项
- **鉴权**: 接口调用需携带 `X-API-Key` 头。
- **配置**: `agents` 模块的配置位于 `agents/config` 或环境变量。
- **网络**: 确保 backend 能够访问 agents 服务地址 (默认 `http://127.0.0.1:8001`)。
