from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class EventType(str, Enum):
    """
    用户学习事件类型枚举
    """
    START_LEARN = "start_learn"
    PAUSE = "pause"
    FINISH = "finish"
    ANSWER_QUIZ = "answer_quiz"
    VIEW_SUMMARY = "view_summary"

class EventLogBase(SQLModel):
    """
    用户事件日志基础模型
    用于记录用户在系统中的学习和交互行为事件
    """
    user_id: int = Field(index=True, description="关联的用户ID，必填项，用于标识事件触发者")
    content_id: Optional[int] = Field(default=None, index=True, description="关联的学习内容ID，可选项，标识事件相关的具体内容")
    event_type: EventType = Field(description="事件类型枚举，必填项，表示具体的行为动作")
    duration_sec: int = Field(default=0, description="事件持续时间，单位：秒，默认值为0")
    score: Optional[float] = Field(default=None, description="事件相关的得分或进度，可选项，例如测验得分")
    meta_info: Optional[str] = Field(default=None, description="附加元数据信息，可选项，以JSON字符串或普通文本格式存储扩展数据")

class EventLog(EventLogBase, table=True):
    """
    用户事件日志数据库表模型
    """
    log_id: Optional[int] = Field(default=None, primary_key=True, description="日志记录唯一ID，主键")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="日志创建时间，默认自动生成当前UTC时间")

class UserProgressBase(SQLModel):
    """
    用户学习进度基础模型
    用于汇总和记录用户的整体学习进度和统计数据
    """
    user_id: int = Field(primary_key=True, description="关联的用户ID，主键，与用户表一对一对应")
    total_study_time_min: float = Field(default=0.0, description="累计学习总时长，单位：分钟，默认值为0.0")
    completion_rate: float = Field(default=0.0, description="整体内容完成率，取值范围0.0-1.0，默认值为0.0")
    accuracy_rate: float = Field(default=0.0, description="测验或练习的整体准确率，取值范围0.0-1.0，默认值为0.0")
    streak_days: int = Field(default=0, description="连续学习打卡天数，默认值为0")
    
class UserProgress(UserProgressBase, table=True):
    """
    用户学习进度数据库表模型
    """
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="最后一次更新时间，默认自动生成当前UTC时间")
    
    # We might want to link this to User table if we want foreign key constraints
    # user: "User" = Relationship(back_populates="progress") 
    # But for now, keeping it simple as ID-based.
