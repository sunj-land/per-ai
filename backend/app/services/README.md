# Services 模块架构与开发文档

## 1. 模块的整体架构设计和职责边界
`backend/app/services` 模块是整个系统的“业务逻辑层（Business Logic Layer）”。它介于表现层（API Routers）与数据访问层（Models/Core）之间，遵循领域驱动设计（DDD）的指导思想，负责封装所有的核心业务规则。

**职责边界**：
- **向上承接 API**：接收来自 `api` 模块的数据，执行业务校验与流程编排，然后返回处理结果。API 层应该非常薄，所有的“重活”都应放在 Service 中。
- **向下操作 ORM**：持有数据库的 `Session`，负责构建复杂的 SQL 查询（如多表 Join、分页、聚合）以及事务的管理（Commit/Rollback）。
- **外部服务协同**：协调调用内部的通信总线（Bus）、第三方网关（Agent Clients）、文件存储（Storage）等外部资源。
- **状态与异常管理**：捕获底层的特定错误，并将其转化为业务层面的异常（如抛出 `HTTPException(404, "User not found")`）。

## 2. 核心组件的详细功能说明
该目录下包含了近 20 个独立的服务类，核心组件包括：
- **`ChatService` (`chat_service.py`)**：负责管理 AI 聊天会话的生命周期。提供创建会话、保存历史消息、组装上下文供大模型推理，并处理 `AgentsServiceSyncClient` 的响应流（NDJSON 解析）。
- **`ChannelService` (`channel_service.py`)**：负责多渠道（QQBot、DingTalk 等）的配置管理、增删改查。它结合 `AdapterFactory`，实现了消息的统一路由和 Webhook 的安全验证与转发。
- **`TaskService` & `AgentService`**：处理异步任务的执行与智能体的调度。它们负责将耗时的操作推入后台，并跟踪任务的状态（Pending, Running, Completed, Failed）。
- **`StorageService` & `FileProcessor`**：负责附件和文件的处理。包括文件的分块上传、图片压缩、文本解析以及生成向量检索所需的文档切片（Chunks）。
- **`RssService`**：负责解析 RSS 订阅源，定期抓取最新文章，并与内部的内容系统（Note/Content）打通，实现信息自动聚合。

## 3. 模块间的交互流程和数据流转
以用户在 Web 端发送一条对话消息为例，其交互流程如下：
1. **API 层调用**：`api/chat.py` 接收到前端请求后，提取出 `session_id` 和 `content`，调用 `chat_service.send_message()`。
2. **Service 数据校验**：`ChatService` 验证 `session_id` 格式（如是否为合法的 UUID），并在数据库中查找对应的 `ChatSession`。
3. **上下文组装**：Service 从数据库中查询该会话的历史消息记录，并按 OpenAI 的标准格式组装成 `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}]` 的列表。
4. **触发模型生成**：Service 并不直接调用 LLM，而是将封装好的数据打包为 `InboundMessage` 投入 `core.bus`，或直接通过 `AgentsServiceAsyncClient` 发送给专用的代理服务。
5. **持久化与响应**：模型流式响应结束后，Service 实例化新的 `ChatMessage` 模型并 `session.commit()` 入库，同时将结果返回给 API 层。

## 4. 关键业务场景的处理流程
**场景一：复杂事务与回滚 (Transactional Rollback)**
- 当业务需要同时修改多个表（例如：创建一个用户，并初始化其默认的 `UserProfile` 和 `ChatSession`）时。
- **处理方式**：在 Service 中开启事务块，如果中间任何一步抛出异常，则执行 `session.rollback()`，确保数据的一致性。

**场景二：大模型调用的权限与路由**
- 后端服务严格禁止直接调用 LLM API（如直接引入 `litellm` 并调用）。
- **处理方式**：所有的模型生成请求必须由 `ChatService` 转发至 `AgentsServiceSyncClient` 或通过内部总线（Bus）路由。Service 需负责注入正确的模型参数和租户认证头。

## 5. 配置参数说明和使用示例
Services 层本身不直接读取 `.env` 配置，而是依赖 `core.config` 的注入。服务通常设计为普通的 Python 类或函数模块。

**服务编写规范示例**：
```python
from sqlmodel import Session, select
from fastapi import HTTPException
from app.models.user import User
import uuid

class UserService:
    """
    用户业务逻辑服务类
    """
    
    @staticmethod
    def get_user_by_id(session: Session, user_id: uuid.UUID) -> User:
        """
        根据用户ID获取用户信息
        :param session: 数据库会话
        :param user_id: 用户唯一标识
        :return: User 模型实例
        :raises HTTPException 404: 当用户不存在时抛出
        """
        # ========== 步骤1：执行主键查询 ==========
        user = session.get(User, user_id)
        
        # ========== 步骤2：判断并抛出业务异常 ==========
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return user
```

## 6. 可能存在的性能瓶颈和优化建议
1. **服务间循环依赖 (Circular Dependency)**：
   - **瓶颈**：随着业务膨胀，`TaskService` 可能会引入 `ChatService`，而 `ChatService` 又想调用 `TaskService`，导致 Python 导入失败。
   - **优化建议**：提取公共逻辑到第三个服务或核心工具类中；或者在方法内部进行延迟导入（Local Import），推荐采用重构架构（如引入事件总线）来彻底解耦。
2. **长耗时请求阻塞 API**：
   - **瓶颈**：如果在 Service 层执行了耗时的网络请求（如同步的 RSS 抓取）且未使用 `async/await`，将导致 FastAPI 的工作线程池枯竭。
   - **优化建议**：所有的外部 I/O 必须使用 `httpx.AsyncClient` 配合 `async def`；极耗时的 CPU 密集型任务应通过 `background_tasks.add_task` 或放入 `core.bus` 异步处理。
3. **过度依赖全量查询**：
   - **瓶颈**：Service 中随手写出 `session.exec(select(Model)).all()`，在数据量达到数万时会导致严重的内存飙升。
   - **优化建议**：强制在所有列表查询的 Service 方法中引入 `skip` 和 `limit` 参数实现物理分页。
