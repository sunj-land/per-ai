from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum
import uuid

class AgentType(str, Enum):
    """
    Agent 类型枚举。
    定义系统中所有可用的 Agent 角色。
    """
    MASTER = "master"   # 主 Agent，作为系统的入口，负责请求分发和任务协调
    ARTICLE = "article" # 文章处理 Agent，专注于文章检索、阅读和总结
    GENERAL = "general" # 通用对话 Agent，处理闲聊和非特定领域的请求

class MessageRole(str, Enum):
    """
    消息角色枚举。
    定义对话消息的发送者身份，符合 OpenAI Chat 格式标准。
    """
    USER = "user"       # 用户发送的消息
    ASSISTANT = "assistant" # AI 助手 (Agent) 生成的回复
    SYSTEM = "system"   # 系统指令，用于设定 Agent 的行为和人设

class AgentMessage(BaseModel):
    """
    Agent 消息模型。
    表示对话历史中的单条消息实体。
    """
    role: MessageRole # 消息发送者角色
    content: str      # 消息文本内容
    metadata: Dict[str, Any] = Field(default_factory=dict) # 额外的元数据（如时间戳、token 数等）

class AgentRequest(BaseModel):
    """
    Agent 请求模型。
    定义外部系统（如 API 网关、CLI）向 Agent 发起的请求结构。
    """
    query: str # 用户的原始查询文本
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4())) # 会话 ID，用于关联上下文，默认自动生成 UUID
    history: List[AgentMessage] = Field(default_factory=list) # 前端传递的临时对话历史（可选，通常由后端 SessionManager 管理）
    parameters: Dict[str, Any] = Field(default_factory=dict) # 额外的请求参数（如模型配置、插件开关等）

class AgentResponse(BaseModel):
    """
    Agent 响应模型。
    定义 Agent 处理完成后返回给调用方的标准响应结构。
    """
    answer: str # Agent 生成的最终回答文本
    source_agent: str # 产生该回答的 Agent 名称（便于追踪是哪个子 Agent 处理的）
    latency_ms: float # 请求处理的总耗时（毫秒）
    metadata: Dict[str, Any] = Field(default_factory=dict) # 响应元数据（如使用的工具列表、迭代次数等）
    error: Optional[str] = None # 如果发生错误，此处包含错误描述；成功则为 None

class IntentType(str, Enum):
    """
    意图类型枚举。
    定义系统能够识别的用户意图分类。
    """
    SEARCH_ARTICLES = "search_articles" # 用户想要搜索或查找文章
    GENERAL_CHAT = "general_chat"       # 用户进行通用闲聊
    UNKNOWN = "unknown"                 # 无法识别的具体意图

class IntentResult(BaseModel):
    """
    意图识别结果模型。
    存储意图分类器的输出结果。
    """
    intent: IntentType # 识别出的意图类型
    confidence: float  # 识别的可信度分数 (0.0 - 1.0)
    extracted_params: Dict[str, Any] = Field(default_factory=dict) # 从查询中提取的关键参数（如搜索关键词、时间范围等）
