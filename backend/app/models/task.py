from sqlmodel import Field, SQLModel, JSON, Column
from datetime import datetime
from uuid import UUID, uuid4
from typing import Optional, Dict

class TaskBase(SQLModel):
    """
    定时任务/后台任务基础模型
    """
    name: str = Field(description="任务名称，必填项，用于直观识别任务用途")
    description: Optional[str] = Field(default=None, description="任务的详细说明描述，非必填")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建或拥有该任务的用户ID，外键关联user表，非必填")
    type: str = Field(description="任务执行类型，必填项，可选值: script(脚本), function(函数), webhook, ai_dialogue(AI对话)")
    payload: str = Field(description="任务具体的执行载荷，必填项(如脚本路径、函数名、Webhook URL、AI提示词等)")
    schedule_type: str = Field(description="调度类型，必填项，可选值: cron(Cron表达式), interval(间隔时间), date(特定日期执行一次)")
    schedule_config: Dict = Field(default={}, sa_column=Column(JSON), description="具体的调度配置参数，JSON格式(如 {'cron': '0 0 * * *'} )，默认空字典")
    is_active: bool = Field(default=True, description="任务是否处于启用状态，布尔值，默认True(启用)")

class Task(TaskBase, table=True):
    """
    任务数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="任务全局唯一标识ID，主键，默认自动生成UUID")
    last_run_at: Optional[datetime] = Field(default=None, description="最近一次实际执行任务的时间戳，非必填")
    next_run_at: Optional[datetime] = Field(default=None, description="根据调度策略计算出的下一次预期执行时间戳，非必填")
    created_at: datetime = Field(default_factory=datetime.now, description="任务创建时间，默认为当前时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="任务最后修改时间，默认为当前时间")

class TaskCreate(TaskBase):
    """
    创建任务请求模型
    """
    pass

class TaskUpdate(SQLModel):
    """
    更新任务请求模型
    """
    name: Optional[str] = Field(default=None, description="更新的任务名称")
    description: Optional[str] = Field(default=None, description="更新的描述")
    type: Optional[str] = Field(default=None, description="更新的任务类型")
    payload: Optional[str] = Field(default=None, description="更新的执行载荷")
    schedule_type: Optional[str] = Field(default=None, description="更新的调度类型")
    schedule_config: Optional[Dict] = Field(default=None, description="更新的调度配置")
    is_active: Optional[bool] = Field(default=None, description="更新的启用状态")

class TaskLog(SQLModel, table=True):
    """
    任务执行日志数据库表模型
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True, description="日志记录全局唯一ID，主键")
    task_id: UUID = Field(foreign_key="task.id", description="关联的任务ID，外键指向task表，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="关联的用户ID，外键指向user表，非必填")
    status: str = Field(description="该次执行的结果状态，必填项，可选值: success(成功), failed(失败), running(执行中)")
    output: Optional[str] = Field(default=None, description="任务执行后的标准输出日志或错误堆栈信息，非必填")
    duration: Optional[float] = Field(default=None, description="该次任务执行消耗的时间，单位为毫秒(ms)，非必填")
    created_at: datetime = Field(default_factory=datetime.now, description="日志生成/任务触发时间，默认为当前时间")
