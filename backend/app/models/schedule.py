from typing import Optional, List, Dict
from datetime import datetime
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from enum import Enum

class Priority(str, Enum):
    """
    优先级枚举类
    """
    HIGH = "high"      # 高优先级
    MEDIUM = "medium"  # 中优先级
    LOW = "low"        # 低优先级

class ReminderType(str, Enum):
    """
    提醒方式枚举类
    """
    NOTIFICATION = "notification"  # 系统通知
    EMAIL = "email"                # 电子邮件
    SMS = "sms"                    # 短信提醒
    WEBHOOK = "webhook"            # Webhook回调

class ScheduleBase(SQLModel):
    """
    日程基础模型，包含日程的核心业务字段
    """
    title: str = Field(description="日程标题，必填项，简明扼要地说明日程内容")
    description: Optional[str] = Field(default=None, description="日程详细描述，非必填，可包含更多背景信息")
    start_time: datetime = Field(description="日程开始时间，必填项，带时区的时间戳", index=True)
    end_time: Optional[datetime] = Field(default=None, description="日程结束时间，非必填，带时区的时间戳", index=True)
    due_time: Optional[datetime] = Field(default=None, description="任务到期时间，非必填，适用于带截止日期的任务")
    priority: Priority = Field(default=Priority.MEDIUM, description="日程优先级，默认值为中(medium)，可选值: high, medium, low", index=True)
    location: Optional[str] = Field(default=None, description="日程地点，非必填，可为物理地址或线上会议链接")
    is_all_day: bool = Field(default=False, description="是否为全天日程，布尔值，默认为False(否)")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="关联的用户ID，外键指向user表，非必填")

class Schedule(ScheduleBase, table=True):
    """
    日程数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="日程唯一标识，主键，默认自动生成UUID")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间，默认为当前时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间，默认为当前时间")

    # 关联关系：一个日程可包含多个提醒，级联删除
    reminders: List["ScheduleReminder"] = Relationship(back_populates="schedule", sa_relationship_kwargs={"cascade": "all, delete"})

class ScheduleReminderBase(SQLModel):
    """
    日程提醒基础模型
    """
    remind_at: datetime = Field(description="触发提醒的具体时间，必填项")
    type: ReminderType = Field(default=ReminderType.NOTIFICATION, description="提醒发送方式，默认值为系统通知(notification)")
    message_template: Optional[str] = Field(default=None, description="自定义提醒内容模板，非必填")

class ScheduleReminder(ScheduleReminderBase, table=True):
    """
    日程提醒数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="提醒记录唯一标识，主键，默认自动生成UUID")
    schedule_id: UUID = Field(foreign_key="schedule.id", description="关联的日程ID，外键指向schedule表")
    status: str = Field(default="pending", description="提醒发送状态，默认值为待发送(pending)，可选值: pending(待发送), sent(已发送), failed(失败)")

    # 关联关系：属于哪一个日程
    schedule: Optional[Schedule] = Relationship(back_populates="reminders")

class ScheduleReminderCreate(ScheduleReminderBase):
    """
    创建日程提醒时的请求模型
    """
    pass

class ScheduleCreate(ScheduleBase):
    """
    创建日程时的请求模型
    """
    reminders: Optional[List[ScheduleReminderCreate]] = Field(default=None, description="创建日程时附带的提醒列表")

class ScheduleUpdate(SQLModel):
    """
    更新日程时的请求模型，所有字段均为可选
    """
    title: Optional[str] = Field(default=None, description="更新的日程标题")
    description: Optional[str] = Field(default=None, description="更新的日程描述")
    start_time: Optional[datetime] = Field(default=None, description="更新的开始时间")
    end_time: Optional[datetime] = Field(default=None, description="更新的结束时间")
    due_time: Optional[datetime] = Field(default=None, description="更新的到期时间")
    priority: Optional[Priority] = Field(default=None, description="更新的优先级")
    location: Optional[str] = Field(default=None, description="更新的地点")
    is_all_day: Optional[bool] = Field(default=None, description="更新的全局全天状态")
    reminders: Optional[List[ScheduleReminderCreate]] = Field(default=None, description="更新的提醒列表，通常为全量替换")
