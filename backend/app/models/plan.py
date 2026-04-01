from typing import List, Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from enum import Enum

class PlanStatus(str, Enum):
    """
    计划状态枚举
    """
    DRAFT = "draft"          # 草稿
    ACTIVE = "active"        # 进行中
    COMPLETED = "completed"  # 已完成
    ARCHIVED = "archived"    # 已归档

class MilestoneStatus(str, Enum):
    """
    里程碑状态枚举
    """
    PENDING = "pending"          # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成

class TaskStatus(str, Enum):
    """
    任务状态枚举
    """
    PENDING = "pending"          # 待开始
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"      # 已完成
    SKIPPED = "skipped"          # 已跳过

class TaskType(str, Enum):
    """
    任务类型枚举
    """
    VIDEO = "video"        # 视频学习
    EXERCISE = "exercise"  # 练习题
    SUMMARY = "summary"    # 总结输出
    READING = "reading"    # 阅读材料
    OTHER = "other"        # 其他类型

# --- Plan Header ---
class PlanHeaderBase(SQLModel):
    """
    学习计划头基础模型
    """
    user_id: int = Field(index=True, description="创建该计划的用户ID，必填项，支持索引")
    goal: str = Field(description="计划的总体目标描述，必填项")
    deadline: datetime = Field(description="计划的整体截止时间，必填项")
    status: PlanStatus = Field(default=PlanStatus.DRAFT, description="计划当前状态，默认值为草稿(draft)")
    estimated_hours: Optional[float] = Field(default=None, description="预计完成计划所需的总小时数，非必填")
    difficulty_coef: float = Field(default=1.0, description="计划的难度系数(例如1.0为标准难度)，默认值为1.0")
    version: int = Field(default=1, description="计划的版本号，默认从1开始")

class PlanHeader(PlanHeaderBase, table=True):
    """
    学习计划头数据库表模型
    """
    plan_id: Optional[int] = Field(default=None, primary_key=True, description="计划主键ID，自动递增")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="计划创建时间(UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="计划最后更新时间(UTC)")

    # 关联关系：一个计划包含多个里程碑
    milestones: List["PlanMilestone"] = Relationship(back_populates="plan")

class PlanHeaderCreate(PlanHeaderBase):
    """
    创建学习计划头请求模型
    """
    pass

class PlanHeaderRead(PlanHeaderBase):
    """
    读取学习计划头响应模型
    """
    plan_id: int = Field(description="计划ID")
    created_at: datetime = Field(description="创建时间")

# --- Plan Milestone ---
class PlanMilestoneBase(SQLModel):
    """
    计划里程碑基础模型
    """
    title: str = Field(description="里程碑的标题名称，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID，外键关联user表，非必填")
    deadline: Optional[datetime] = Field(default=None, description="该里程碑的具体截止时间，非必填")
    status: MilestoneStatus = Field(default=MilestoneStatus.PENDING, description="里程碑状态，默认待开始(pending)")
    order_index: int = Field(default=0, description="里程碑在计划中的排序权重，数字越小越靠前，默认0")

class PlanMilestone(PlanMilestoneBase, table=True):
    """
    计划里程碑数据库表模型
    """
    milestone_id: Optional[int] = Field(default=None, primary_key=True, description="里程碑主键ID")
    plan_id: int = Field(foreign_key="planheader.plan_id", description="所属的计划ID，外键关联planheader表")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="里程碑创建时间(UTC)")

    # 关联关系：所属的计划
    plan: PlanHeader = Relationship(back_populates="milestones")
    # 关联关系：一个里程碑包含多个具体任务
    tasks: List["PlanTask"] = Relationship(back_populates="milestone")

class PlanMilestoneCreate(PlanMilestoneBase):
    """
    创建里程碑请求模型
    """
    plan_id: int = Field(description="所属的计划ID")

class PlanMilestoneRead(PlanMilestoneBase):
    """
    读取里程碑响应模型
    """
    milestone_id: int = Field(description="里程碑ID")
    plan_id: int = Field(description="所属的计划ID")

# --- Plan Task ---
class PlanTaskBase(SQLModel):
    """
    计划具体任务基础模型
    """
    title: str = Field(description="任务的标题名称，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID，外键关联user表，非必填")
    type: TaskType = Field(default=TaskType.OTHER, description="任务的具体类型，默认other(其他)")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务执行状态，默认pending(待开始)")
    estimated_min: int = Field(default=30, description="任务预计完成所需的时间，单位为分钟(min)，默认30分钟")
    order_index: int = Field(default=0, description="任务在里程碑内的排序权重，默认0")
    description: Optional[str] = Field(default=None, description="任务的详细描述或指引，非必填")

class PlanTask(PlanTaskBase, table=True):
    """
    计划具体任务数据库表模型
    """
    task_id: Optional[int] = Field(default=None, primary_key=True, description="任务主键ID")
    milestone_id: int = Field(foreign_key="planmilestone.milestone_id", description="所属的里程碑ID，外键关联planmilestone表")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="任务创建时间(UTC)")

    # 关联关系：所属的里程碑
    milestone: PlanMilestone = Relationship(back_populates="tasks")
    # 关联关系：一个任务可包含多个内容资源
    contents: List["ContentRepo"] = Relationship(back_populates="task")

class PlanTaskCreate(PlanTaskBase):
    """
    创建任务请求模型
    """
    milestone_id: int = Field(description="所属的里程碑ID")

class PlanTaskRead(PlanTaskBase):
    """
    读取任务响应模型
    """
    task_id: int = Field(description="任务ID")
    milestone_id: int = Field(description="所属的里程碑ID")

# --- Composite Models for Creation ---
class PlanTaskCreateNested(PlanTaskBase):
    """
    嵌套创建任务的请求模型
    """
    pass

class PlanMilestoneCreateNested(PlanMilestoneBase):
    """
    嵌套创建里程碑的请求模型
    """
    tasks: List[PlanTaskCreateNested] = Field(default=[], description="包含的任务列表")

class PlanCreateFull(PlanHeaderBase):
    """
    完整创建计划(含里程碑、任务)的请求模型
    """
    milestones: List[PlanMilestoneCreateNested] = Field(default=[], description="包含的里程碑列表")
