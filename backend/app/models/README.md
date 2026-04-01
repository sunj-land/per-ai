# Models 模块架构与开发文档

## 1. 模块的整体架构设计和职责边界
`backend/app/models` 模块是系统数据的基石，负责所有核心领域实体（Domain Entities）的定义与数据库表结构的映射。本模块基于 **SQLModel**（结合了 Pydantic 和 SQLAlchemy 的现代 ORM 框架）构建。

**职责边界**：
- **数据结构定义**：严格定义所有数据库表的字段、类型、默认值以及约束条件。
- **关系映射**：使用 SQLModel 的 `Relationship` 特性，定义模型间的一对一、一对多和多对多关系。
- **数据验证与序列化**：借助底层的 Pydantic，在数据入库前进行自动校验，并在 API 响应时作为序列化的基准（如使用 `.dict()` 或模型切片）。
- **纯粹的数据模型**：该模块**不应包含任何复杂的业务逻辑**，所有数据库查询（CRUD）和事务管理均应下放至 `services` 模块处理。

## 2. 核心组件的详细功能说明
- **`Chat` 体系 (`chat.py`)**：
  - `ChatSession`：表示一次对话会话，包含标题、所用模型（如 GPT-4）、系统提示词等元数据。
  - `ChatMessage`：记录每一条对话内容，包含角色（User/Assistant）、文本内容、Tokens 消耗、思考过程（Reasoning）、卡片引用（Cards）以及相关的附件（Attachments）。
- **`User` 体系 (`user.py`, `user_profile.py`)**：
  - `User`：核心用户模型，存储用户名、邮箱、密码哈希、角色权限等基础认证信息。
  - `UserProfile`：用户偏好与资料扩展模型，包含头像、主题偏好等。
- **`Channel` 体系 (`channel.py`)**：
  - `Channel`：存储渠道配置（如 QQBot、钉钉），其中 `config` 字段使用 JSON 类型存储不同渠道特有的密钥与参数。
  - `ChannelMessage`：记录通过各个渠道收发的消息流转历史。
- **任务与调度体系 (`task.py`, `schedule.py`, `plan.py`)**：
  - 定义了系统的异步任务、定时计划及执行记录，常用于 AI 自动化 Agent 的运行状态跟踪。
- **内容与附件体系 (`content.py`, `attachment.py`, `note.py`)**：
  - `Attachment`：统一管理上传的文件（图片、文档等），包含文件的 S3 路径、大小、MIME 类型。
  - `Note`：个人的笔记与知识库存储单元。

## 3. 模块间的交互流程和数据流转
数据模型本身不直接参与交互流程，而是作为数据流转的载体（Payload）。
典型的流转路径如下：
1. **API 层接收数据**：FastAPI 根据定义的 Pydantic Schema（通常直接使用或继承自 SQLModel）解析并校验 HTTP Request Body。
2. **Service 层组装**：服务层（如 `chat_service.py`）将校验后的数据或外部调用的结果实例化为具体的 Model 对象（例如 `ChatMessage(content="Hello", role="user", session_id=sid)`）。
3. **ORM 提交入库**：Service 层通过注入的数据库 `Session` 执行 `session.add(model_instance)` 和 `session.commit()`。SQLModel 会将其转化为原生的 SQL 语句（Insert/Update）并写入 SQLite。
4. **API 层返回数据**：从数据库查询出 Model 实例后，FastAPI 自动将其转换为 JSON 响应给前端。

## 4. 关键业务场景的处理流程
**场景一：定义一对多关联模型 (ChatSession 与 ChatMessage)**
- **处理方式**：在 `ChatSession` 中定义 `messages: list["ChatMessage"] = Relationship(back_populates="session")`。在 `ChatMessage` 中定义外键 `session_id: uuid.UUID = Field(foreign_key="chatsession.id")` 并配置对应的反向引用。
- **效果**：在查询 `ChatSession` 时，可以通过 `selectinload` 预加载所有的历史消息，极大简化了业务代码并避免了 N+1 查询问题。

**场景二：存储动态/不规则配置数据 (JSON 字段)**
- **处理方式**：在 `Channel` 模型的 `config` 字段中，利用 SQLAlchemy 的 `JSON` 类型。
- **代码实现**：`config: dict = Field(default_factory=dict, sa_column=Column(JSON))`。这允许同一张表存储结构迥异的配置（如钉钉只需 Webhook，而 QQBot 需要 AppID 等多个字段）。

## 5. 配置参数说明和使用示例
由于是模型定义，核心配置在于如何正确书写字段和约束。

**示例：如何定义一个标准的数据模型**
```python
import uuid
from typing import Optional, Dict
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field, Column, JSON

class MyFeature(SQLModel, table=True):
    """
    MyFeature 业务功能的数据模型
    """
    # ========== 步骤1：定义主键 ==========
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    
    # ========== 步骤2：定义基础字段与约束 ==========
    name: str = Field(index=True, max_length=100)
    description: Optional[str] = Field(default=None)
    
    # ========== 步骤3：定义特殊类型（如 JSON） ==========
    extra_data: Dict = Field(default_factory=dict, sa_column=Column(JSON))
    
    # ========== 步骤4：定义时间戳 ==========
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```
*注：严禁使用 `metadata` 作为字段名，因为它是 SQLAlchemy 的内部保留关键字。*

## 6. 可能存在的性能瓶颈和优化建议
1. **N+1 查询问题**：
   - **瓶颈**：当查询列表（如查询 100 个 `ChatSession`）并在循环中访问每个 session 的 `messages` 时，SQLAlchemy 默认会触发懒加载（Lazy Load），导致产生 101 条 SQL 查询。
   - **优化建议**：在 `services` 模块编写查询时，必须强制使用 `selectinload` 或 `joinedload`：`session.exec(select(ChatSession).options(selectinload(ChatSession.messages)))`。
2. **大字段（TEXT/JSON）全表扫描**：
   - **瓶颈**：如果表中包含非常大的 JSON 或文本字段（如 `ChatMessage` 中的 `content`），执行 `select *` 会消耗大量内存和网络带宽。
   - **优化建议**：在列表查询 API 中，明确使用 `select(Model.id, Model.title)` 进行投影查询，避免拉取大字段；只在详情查询时获取全量数据。
3. **缺少索引**：
   - **瓶颈**：当数据量达到十万级别，通过 `user_id` 或特定状态（如 `status`）进行查询时会非常缓慢。
   - **优化建议**：对于频繁用于 `WHERE` 或 `ORDER BY` 的字段，必须在 Field 中显式声明 `index=True`。
