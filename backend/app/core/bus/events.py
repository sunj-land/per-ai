"""
事件总线使用的数据结构定义
包含入站消息和出站消息的实体模型，用于规范渠道与核心处理逻辑之间的数据交互
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """
    入站消息实体模型
    表示从外部聊天渠道（如 web, qqbot 等）接收到的用户消息
    """
    # 消息来源渠道标识，例如: "web", "qqbot"
    channel: str
    
    # 发送者唯一标识符 (用户ID或OpenID)
    sender_id: str
    
    # 会话或群组的唯一标识符 (在web中通常是 session_id)
    chat_id: str
    
    # 消息的正文文本内容
    content: str
    
    # 消息的接收时间，默认当前时间
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 消息附带的媒体资源URL列表（如图片）
    media: list[str] = field(default_factory=list)
    
    # 渠道特定的额外元数据字典
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # 会话键重写：用于支持特定线程范围的会话隔离
    session_key_override: str | None = None

    @property
    def session_key(self) -> str:
        """
        获取用于标识唯一会话的键值
        优先使用覆盖键，否则采用 "渠道:会话ID" 的组合格式
        :return: 唯一会话键字符串
        """
        return self.session_key_override or f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """
    出站消息实体模型
    表示由 AI 生成或系统发出，需要发送给外部聊天渠道的消息
    """
    # 目标渠道标识，例如: "web", "qqbot"
    channel: str
    
    # 目标会话或群组的唯一标识符
    chat_id: str
    
    # 消息的正文文本内容
    content: str
    
    # 可选，需要回复的特定消息ID
    reply_to: str | None = None
    
    # 消息附带的媒体资源URL列表
    media: list[str] = field(default_factory=list)
    
    # 渠道特定的额外元数据字典（例如用于 web 的 response_queue）
    metadata: dict[str, Any] = field(default_factory=dict)


