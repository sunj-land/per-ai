from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel
from enum import Enum

class ReminderMethod(str, Enum):
    """
    提醒方式枚举
    """
    WEB = "web"
    EMAIL = "email"
    WEBHOOK = "webhook"
    SMS = "sms"

class UserReminderBase(SQLModel):
    """
    用户提醒设置基础模型
    用于定义用户级别的通用提醒规则和渠道配置
    """
    user_id: int = Field(index=True, description="关联的用户ID，必填项，建立用户与提醒设置的关联")
    cron_expression: str = Field(default="0 9 * * *", description="Cron定时表达式，决定提醒触发时间，默认每天上午9点")
    method: ReminderMethod = Field(default=ReminderMethod.WEB, description="提醒发送方式枚举，默认值为站内信(WEB)")
    enabled: bool = Field(default=True, description="提醒规则是否启用，默认开启(True)")
    message_template: Optional[str] = Field(default=None, description="自定义提醒消息模板，可选项，支持变量替换")
    target_url: Optional[str] = Field(default=None, description="目标推送地址，主要用于Webhook或外部接口调用时的目标URL，可选项")

class UserReminder(UserReminderBase, table=True):
    """
    用户提醒设置数据库表模型
    """
    reminder_id: Optional[int] = Field(default=None, primary_key=True, description="提醒规则唯一ID，主键")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="提醒规则创建时间，默认自动生成当前UTC时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="提醒规则更新时间，默认自动生成当前UTC时间")

class UserReminderCreate(UserReminderBase):
    """
    创建用户提醒设置的请求模型
    """
    pass

class UserReminderRead(UserReminderBase):
    """
    读取用户提醒设置的响应模型
    """
    reminder_id: int = Field(description="提醒规则唯一ID")
    created_at: datetime = Field(description="提醒规则创建时间")
