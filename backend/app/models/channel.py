from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import SQLModel, Field, JSON, Column, Relationship

class ChannelBase(SQLModel):
    """
    消息渠道基础模型
    """
    name: str = Field(index=True, description="渠道名称，必填项，支持索引以便快速查找")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建该渠道的用户ID，外键关联user表，非必填")
    description: Optional[str] = Field(default=None, description="渠道的详细描述信息，非必填")
    type: str = Field(description="渠道类型，必填，可选值: dingtalk(钉钉), feishu(飞书), wechat_work(企业微信), slack, email(邮件), webhook, discord, teams")
    config: Dict = Field(default={}, sa_column=Column(JSON), description="渠道的连接配置信息(如Token、Secret等)，JSON字典格式，默认空字典")
    is_active: bool = Field(default=True, description="渠道是否处于激活可用状态，布尔值，默认True(是)")

class Channel(ChannelBase, table=True):
    """
    消息渠道数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="渠道唯一标识，主键，默认自动生成UUID")
    created_at: datetime = Field(default_factory=datetime.now, description="渠道创建时间，默认为当前时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="渠道最后更新时间，默认为当前时间")

    # 关联关系：一个渠道可以发送多条消息
    messages: List["ChannelMessage"] = Relationship(back_populates="channel")

class ChannelMessageBase(SQLModel):
    """
    渠道消息基础模型
    """
    channel_id: UUID = Field(foreign_key="channel.id", description="发送消息所使用的渠道ID，外键关联channel表")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="触发该消息发送的用户ID，外键关联user表，非必填")
    content: str = Field(description="消息正文内容或发送给第三方API的JSON Payload数据，必填项")
    status: str = Field(description="消息发送状态，必填项，可选值: pending(发送中), success(发送成功), failed(发送失败)")
    result: Optional[str] = Field(default=None, description="第三方API的原始响应结果或错误信息，非必填")

class ChannelMessage(ChannelMessageBase, table=True):
    """
    渠道消息数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="消息记录唯一标识，主键，默认自动生成UUID")
    created_at: datetime = Field(default_factory=datetime.now, description="消息记录创建时间，默认为当前时间")

    # 关联关系：所属的消息渠道
    channel: Optional[Channel] = Relationship(back_populates="messages")

class ChannelCreate(ChannelBase):
    """
    创建渠道请求模型
    """
    pass

class ChannelUpdate(SQLModel):
    """
    更新渠道请求模型
    """
    name: Optional[str] = Field(default=None, description="更新的渠道名称")
    description: Optional[str] = Field(default=None, description="更新的描述信息")
    type: Optional[str] = Field(default=None, description="更新的渠道类型")
    config: Optional[Dict] = Field(default=None, description="更新的配置信息")
    is_active: Optional[bool] = Field(default=None, description="更新的激活状态")

class ChannelMessageCreate(ChannelMessageBase):
    """
    创建渠道消息请求模型
    """
    pass
