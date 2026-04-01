from typing import Optional, Dict
from enum import Enum
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, JSON, Column
from .plan import PlanTask, TaskType

class ContentType(str, Enum):
    """
    内容类型枚举
    """
    VIDEO = "video"  # 视频内容
    TEXT = "text"    # 文本内容
    QUIZ = "quiz"    # 测验/问卷
    AUDIO = "audio"  # 音频内容
    PDF = "pdf"      # PDF文档

class ContentRepoBase(SQLModel):
    """
    内容资源库基础模型
    """
    task_id: int = Field(foreign_key="plantask.task_id", index=True, description="关联的具体计划任务ID，外键关联plantask表")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="上传或归属的用户ID，外键关联user表")
    content_type: ContentType = Field(description="内容的具体类型(视频、文本、PDF等)，必填")
    url: Optional[str] = Field(default=None, description="内容的外部或内部链接URL，非必填")
    text: Optional[str] = Field(default=None, description="如果是纯文本内容，这里直接存储文本正文，非必填")
    title: str = Field(description="内容资源的标题，必填项")
    duration_sec: Optional[int] = Field(default=None, description="内容的持续时间或预估消费时间，单位为秒(s)，非必填")
    difficulty: float = Field(default=0.5, description="内容难度系数，范围建议0.0-1.0，默认为0.5(中等难度)")
    tags: Optional[str] = Field(default=None, description="内容的标签集合，使用逗号分隔的字符串，非必填")
    meta_data: Optional[Dict] = Field(default={}, sa_column=Column(JSON), description="扩展的元数据信息(如视频分辨率、PDF页数等)，JSON格式存储")
    # metadata is reserved in SQLAlchemy

class ContentRepo(ContentRepoBase, table=True):
    """
    内容资源库数据库表模型
    """
    content_id: Optional[int] = Field(default=None, primary_key=True, description="内容资源的主键ID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="内容的创建或入库时间(UTC)")
    
    # 关联关系：所属的计划任务
    task: Optional[PlanTask] = Relationship(back_populates="contents")

class ContentRepoCreate(ContentRepoBase):
    """
    创建内容资源的请求模型
    """
    pass

class ContentRepoRead(ContentRepoBase):
    """
    读取内容资源的响应模型
    """
    content_id: int = Field(description="内容资源ID")
    created_at: datetime = Field(description="创建时间")
