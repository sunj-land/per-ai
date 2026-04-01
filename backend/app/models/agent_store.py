from typing import Optional, Any
from datetime import datetime
import uuid
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON, Text

class AgentModelBase(SQLModel):
    """
    AI Agent代理基础模型
    """
    name: str = Field(unique=True, index=True, description="Agent唯一系统名称，必填项，用于内部标识和检索")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建或拥有该Agent的用户ID，外键关联user表，非必填")
    description: Optional[str] = Field(default=None, description="Agent的功能描述信息，非必填")
    type: str = Field(default="standard", description="Agent的具体类型，默认为标准(standard)，可选值: workflow(工作流), standard(标准)")
    status: str = Field(default="active", description="Agent当前的生命周期状态，默认为活跃(active)，可选值: active, inactive")
    config: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Agent的详细配置信息(如提示词、模型参数等)，JSON格式存储，非必填")

class AgentModel(AgentModelBase, table=True):
    """
    AI Agent代理存储表模型
    """
    __tablename__ = "agent_store"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Agent唯一全局ID，主键，默认自动生成UUID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间(UTC)，默认当前时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="记录最后更新时间(UTC)，默认当前时间")

class SkillModelBase(SQLModel):
    """
    技能/插件基础模型
    """
    name: str = Field(unique=True, index=True, description="Skill唯一系统名称，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="归属的用户ID，外键关联user表，非必填")
    version: str = Field(default="0.1.0", index=True, description="Skill当前的版本号(遵循SemVer)，默认0.1.0")
    description: Optional[str] = Field(default=None, description="Skill的详细说明描述，支持Markdown格式，非必填")
    author: Optional[str] = Field(default=None, description="Skill的作者名称或机构，非必填")
    tags: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Skill的分类标签列表，JSON数组格式存储，非必填")
    source_type: str = Field(default="local", description="Skill的获取来源类型，默认为本地(local)，可选值: local, registry(注册中心), url(远程地址)")
    source_url: Optional[str] = Field(default=None, description="Skill的源代码仓库地址或主页，非必填")
    install_url: Optional[str] = Field(default=None, description="Skill的具体安装包下载URL，非必填")
    file_path: Optional[str] = Field(default=None, description="如果是本地Skill，对应的内部存储文件路径，非必填")
    install_dir: Optional[str] = Field(default=None, description="Skill在系统中的安装部署目录，非必填")
    status: str = Field(default="active", description="Skill启用状态，默认活跃(active)，可选值: active(活跃), error(异常)")
    install_status: str = Field(default="installed", description="Skill安装状态，默认已安装(installed)，可选值: pending, installing, installed, failed, uninstalled")
    dependency_snapshot: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="安装时的依赖包快照记录，JSON格式存储，非必填")
    idempotency_key: Optional[str] = Field(default=None, index=True, description="防止重复操作的幂等键，非必填")
    last_install_at: Optional[datetime] = Field(default=None, description="最后一次执行安装的时间戳，非必填")
    last_error: Optional[str] = Field(default=None, sa_column=Column(Text), description="最近一次运行时产生的错误详细信息，文本格式，非必填")
    is_deleted: bool = Field(default=False, description="逻辑删除标记，布尔值，默认False(未删除)")
    input_schema: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Skill调用的输入参数Schema(JSON Schema格式)，非必填")
    output_schema: Optional[Any] = Field(default=None, sa_column=Column(JSON), description="Skill调用的返回结果Schema(JSON Schema格式)，非必填")

class SkillModel(SkillModelBase, table=True):
    """
    技能/插件存储表模型
    """
    __tablename__ = "skill_store"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="Skill唯一全局ID，主键，默认自动生成UUID")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间(UTC)，默认当前时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="记录最后更新时间(UTC)，默认当前时间")

class SkillInstallRecordModel(SQLModel, table=True):
    """
    技能安装操作记录表模型
    """
    __tablename__ = "skill_install_record"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="安装操作记录的唯一ID，主键")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="发起操作的用户ID，外键关联user表，非必填")
    task_id: str = Field(index=True, description="后台异步安装任务的ID，必填项")
    skill_name: str = Field(index=True, description="操作涉及的Skill名称，必填项")
    target_version: str = Field(default="latest", description="目标安装版本，默认为最新版(latest)")
    operation: str = Field(default="install", description="具体操作类型，默认安装(install)，可选值: install(安装), upgrade(升级), uninstall(卸载)")
    status: str = Field(default="pending", description="任务执行状态，默认待处理(pending)，可选值: pending, running, success, failed")
    operator: Optional[str] = Field(default=None, description="执行该操作的用户标识或系统标识，非必填")
    idempotency_key: Optional[str] = Field(default=None, index=True, description="操作的幂等键，非必填")
    result_message: Optional[str] = Field(default=None, sa_column=Column(Text), description="操作完成后的结果摘要消息，非必填")
    log_summary: Optional[str] = Field(default=None, sa_column=Column(Text), description="操作执行过程的日志摘要，非必填")
    started_at: datetime = Field(default_factory=datetime.utcnow, description="操作实际开始执行的时间(UTC)")
    finished_at: Optional[datetime] = Field(default=None, description="操作执行完成的时间(UTC)，非必填")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间(UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="记录最后更新时间(UTC)")

class SkillDependencyModel(SQLModel, table=True):
    """
    技能依赖关系表模型
    """
    __tablename__ = "skill_dependency"
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True, description="依赖关系记录的唯一ID，主键")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID，非必填")
    skill_name: str = Field(index=True, description="宿主Skill的名称，必填项")
    skill_version: str = Field(default="0.1.0", description="宿主Skill的版本，默认0.1.0")
    dependency_name: str = Field(index=True, description="依赖包/库的名称，必填项")
    required_version: str = Field(default="*", description="依赖包所需的版本约束表达式(如 >=1.0.0)，默认不限制(*)")
    resolved_version: Optional[str] = Field(default=None, description="实际解析并安装的具体版本号，非必填")
    source: str = Field(default="registry", description="依赖的拉取源类型，默认注册中心(registry)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="记录创建时间(UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="记录最后更新时间(UTC)")
