from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship
import uuid
from sqlalchemy import Column, JSON

class ChatSessionBase(SQLModel):
    """
    聊天会话基础数据模型
    定义了聊天会话的通用基础属性，供请求验证和数据库模型继承使用
    """
    # 会话标题：用于在侧边栏显示的聊天名称
    title: str = Field(default="New Chat", description="会话标题，默认为'New Chat'")

    # 用户ID：关联到 User 表的主键，表示该会话属于哪个用户（可为空表示匿名）
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="会话所属用户ID，外键关联user表，可为空表示匿名或公共会话")

    # 分享标识：当会话被公开分享时生成的唯一标识符
    share_id: Optional[str] = Field(default=None, description="公开分享时的唯一标识符(UUID/Hash)，非必填")

class ChatSession(ChatSessionBase, table=True):
    """
    聊天会话数据库实体模型
    映射到底层的 chatsession 物理表，包含主键和时间戳
    """
    # 会话唯一主键：自动生成的 UUID
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="会话全局唯一ID，主键，默认自动生成UUID")

    # 创建时间：记录会话发起的 UTC 时间
    created_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc), description="会话创建时间，UTC时间，默认当前时间")

    # 更新时间：记录会话最后一次发生交互的时间
    updated_at: datetime = Field(default_factory=lambda: datetime.now(datetime.timezone.utc), description="会话最后更新时间，UTC时间，默认当前时间")

    # 一对多关系映射：当前会话包含的所有消息列表，级联删除
    messages: List["ChatMessage"] = Relationship(back_populates="session", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

class ChatMessageBase(SQLModel):
    """
    聊天消息基础数据模型
    定义单条消息的结构，支持多模态数据（图片、附件）及元数据扩展
    """
    # 发送者角色：如 'user', 'assistant', 'system'
    role: str = Field(description="消息发送者角色，必填，可选值: user(用户), assistant(AI助手), system(系统提示词)")

    # 用户ID：发送消息的用户标识
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="发送该消息的用户ID，外键关联user表")

    # 消息正文：具体的文本内容
    content: str = Field(description="消息的正文文本内容，必填")

    # 图片列表：存放关联图片的 URL，JSON格式
    images: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description="消息附带的图片URL列表，JSON格式存储，非必填")

    # 附件列表：存放关联附件的 UUID 集合，JSON格式
    attachments: Optional[List[str]] = Field(default=None, sa_column=Column(JSON), description="消息附带的附件UUID列表，JSON格式存储，非必填")

    # 用户反馈：记录对 AI 回复的评价（like/dislike）
    feedback: Optional[str] = Field(default=None, description="用户对该条AI回复的反馈，可选值: like(点赞), dislike(点踩)")

    # 收藏标记：标识用户是否收藏了该消息
    is_favorite: bool = Field(default=False, description="该消息是否被用户收藏，布尔值，默认False(否)")

    # 扩展字典：存储模型消耗、推理过程(reasoning)、引用来源等非结构化数据
    extra: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="扩展信息字典(如引用来源、Token消耗等)，JSON格式存储，非必填")

class ChatMessage(ChatMessageBase, table=True):
    """
    聊天消息数据库实体模型
    映射到底层的 chatmessage 物理表，关联具体的 ChatSession
    """
    # 消息唯一主键：自动生成的 UUID
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="消息全局唯一ID，主键，默认自动生成UUID")

    # 外键：关联到所属的 ChatSession 表
    session_id: uuid.UUID = Field(foreign_key="chatsession.id", description="所属会话的ID，外键关联chatsession表")

    # 发送时间：记录消息创建的 UTC 时间
    created_at: datetime = Field(default_factory=datetime.utcnow, description="消息发送时间，UTC时间，默认当前时间")

    # 多对一关系映射：反向关联所属的会话对象
    session: ChatSession = Relationship(back_populates="messages")

class ChatSessionRead(ChatSessionBase):
    """
    聊天会话读取响应模型 (API 输出)
    用于 FastAPI 序列化返回给前端的数据结构
    """
    # 会话唯一标识
    id: uuid.UUID = Field(description="会话ID")
    # 会话创建时间
    created_at: datetime = Field(description="创建时间")
    # 会话更新时间
    updated_at: datetime = Field(description="更新时间")

class ChatMessageRead(ChatMessageBase):
    """
    聊天消息读取响应模型 (API 输出)
    用于组装消息及其关联的附件详情供前端展示
    """
    # 消息唯一标识
    id: uuid.UUID = Field(description="消息ID")
    # 消息发送时间
    created_at: datetime = Field(description="创建时间")
    # 组装后的附件详情列表（非数据库字段，动态组装）
    attachment_objs: Optional[List[dict]] = Field(default=None, description="附件详细信息列表")
