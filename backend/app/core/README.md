# Core 模块架构与开发文档

## 1. 模块整体架构设计和职责边界
`backend/app/core` 目录是整个后端服务的心脏，承担了所有核心基础组件的实现与维护。该模块遵循“高内聚、低耦合”的设计原则，对外提供稳定且一致的基础服务接口，而对内封装了所有与业务逻辑无关的基础设施层代码。

**职责边界**：
- **基础设施层 (Infrastructure)**：包括数据库连接管理、缓存、向量存储、调度器、日志记录。
- **通信总线层 (Message Bus)**：通过内部异步队列实现各个组件间（如 Web、QQBot、后台任务）的解耦和事件分发。
- **渠道适配层 (Channel Adapters)**：负责统一对接各类第三方即时通讯平台，详见 `core/channel`。
- **第三方集成层 (Third-party Integration)**：如大模型服务提供商 (AI Providers) 的配置管理与认证解析。

## 2. 核心组件的详细功能说明
- **数据库组件 (`database.py`)**：基于 SQLModel 和 SQLAlchemy 构建。启用了 SQLite 的 WAL（Write-Ahead Logging）模式以提升并发读写性能，并提供数据库会话的生成器（Generator）供依赖注入使用。
- **事件总线与调度 (`bus/`)**：
  - `agent_loop.py`：智能体事件循环，负责接收上游（Web/QQ 等）的 `InboundMessage`，调用大模型（LiteLLM）进行处理，并分发错误和流式响应。
  - `dispatcher.py`：消息分发器，将生成好的 `OutboundMessage` 按源渠道（Channel ID）路由回对应的适配器发送。
  - `queue.py` & `events.py`：定义了全局的异步队列（`asyncio.Queue`）和标准化的数据类（DataClass），保证消息结构的一致性。
- **认证与安全 (`auth.py`)**：处理 JWT Token 的签发与验证，为系统的接口请求提供安全屏障。
- **模型提供商配置 (`ai_providers.py`)**：解析并管理 `model-config.json`，将不同的模型映射到其对应的 API Key 与后端网关（Agents Service）。
- **向量存储与文本处理 (`vector_store.py`, `text_splitter.py`)**：为 RAG（检索增强生成）提供基础能力，支持文档的切片、嵌入（Embedding）及相似度检索。
- **定时调度 (`scheduler.py`)**：基于 `APScheduler` 实现的异步定时任务管理，支持后台定期执行 RSS 抓取、系统备份等周期性任务。

## 3. 模块间的交互流程和数据流转
核心模块主要通过“事件驱动”和“依赖注入”两种方式进行数据流转。
以一条用户消息的处理流程为例：
1. **输入端接收**：用户通过 `api/chat.py` 发起请求，系统将其封装为 `InboundMessage` 数据结构。
2. **入队与分发**：消息被推送至 `core/bus/queue.py` 的全局队列中，实现请求的初步解耦。
3. **事件循环处理**：`agent_loop.py` 中的消费者（Consumer）异步取出消息，解析其中的 `chat_id` 与 `channel`。接着根据 `ai_providers.py` 的配置，携带正确的认证信息调用 LLM 接口。
4. **输出流转**：LLM 产生的流式响应（Chunk）被封装为 `OutboundMessage`，随后交由 `dispatcher.py` 进行路由。
5. **渠道适配发送**：分发器通过 `core/channel/factory.py` 获取对应的渠道适配器（如 Web 或 QQBot），最终将消息推送回给用户。

## 4. 关键业务场景的处理流程
**场景一：系统初始化与依赖注入**
- 系统启动时，`main.py` 会调用 `database.create_db_and_tables()` 确保表结构完整。
- 接着加载 `logging_config.py`，配置按天轮转的日志处理器。
- 最后启动 `agent_loop.start_loop()` 和 `dispatcher.start_dispatcher()` 作为常驻的后台协程，等待处理消息。

**场景二：大模型提供商的动态切换**
- 当用户在前端切换模型（例如从 `gpt-4` 切换为 `qwen3-vl`）时，系统会在 `agent_loop.py` 中捕获 `model_id`。
- 通过引入 `ai_providers.py`，系统自动判断前缀（如 `dashscope/`），并从环境变量中提取 `DASHSCOPE_API_KEY`，动态注入给 LiteLLM，从而避免了硬编码。

## 5. 配置参数说明和使用示例
Core 模块严重依赖系统环境变量（位于根目录的 `.env` 文件）和配置字典。
主要配置项包括：
- `DATABASE_URL`：数据库连接字符串，默认使用 `sqlite:///./perall.db`。
- `JWT_SECRET_KEY`：用于签发和验证 Token 的密钥。
- 各种模型 API Keys：如 `OPENAI_API_KEY`, `DASHSCOPE_API_KEY`, `TAVILY_API_KEY`。

**使用示例（数据库会话注入）**：
```python
# 引入核心数据库生成器
from app.core.database import get_session

@router.get("/users")
def get_users(session: Session = Depends(get_session)):
    # ========== 步骤1：获取数据库会话并执行查询 ==========
    return session.exec(select(User)).all()
```

## 6. 可能存在的性能瓶颈和优化建议
1. **SQLite 并发写入瓶颈**：
   - **瓶颈**：目前使用 SQLite WAL 模式，虽然提升了读性能，但多协程同时写入时仍可能出现锁争用（Database is locked）。
   - **优化建议**：对于高并发写入的表（如 `ChatMessage`），考虑在应用层引入写队列批量入库，或在未来迁移至 PostgreSQL。
2. **异步队列阻塞**：
   - **瓶颈**：`agent_loop.py` 中的 LLM 请求如果因为网络原因超时，可能会阻塞当前处理协程，导致队列积压。
   - **优化建议**：引入并发限制器（如 `asyncio.Semaphore`）并在调用 `litellm` 时严格设置 `timeout`，同时增加死信队列（DLQ）机制以保存失败的任务。
3. **向量检索延迟**：
   - **瓶颈**：目前向量检索直接在本地通过 Python 逻辑运算完成，当数据量增加时响应会显著变慢。
   - **优化建议**：集成专用的向量数据库（如 Milvus 或 Qdrant），将计算压力从应用层转移至专业的存储层。
