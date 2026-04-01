from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class UserProfile(SQLModel, table=True):
    """
    用户个人信息模型
    用于存储用户的Soul Identity、Personal Rules等个性化信息
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="个人信息配置记录的主键ID")
    identity: str = Field(default="", description="Soul Identity / 用户身份设定，用于AI对话等场景的系统提示词设定")
    rules: str = Field(default="", description="Personal Rules / 个性化规则，用户设定的个人偏好、回复风格等规则")

    created_at: datetime = Field(default_factory=datetime.utcnow, description="配置首次创建时间(UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="配置最后更新时间(UTC)")

class UserProfileUpdate(SQLModel):
    """
    用户个人信息更新请求模型
    """
    identity: Optional[str] = Field(default=None, description="更新的用户身份设定")
    rules: Optional[str] = Field(default=None, description="更新的个性化规则")

class UserProfileHistory(SQLModel, table=True):
    """
    用户个人信息历史记录
    用于记录用户配置变更的审计日志
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="历史记录主键ID")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="归属的用户ID，外键关联user表")
    profile_id: int = Field(foreign_key="userprofile.id", description="关联的UserProfile的主键ID，外键关联userprofile表")
    identity: str = Field(description="历史版本中的用户身份设定快照")
    rules: str = Field(description="历史版本中的个性化规则快照")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="该快照版本的生成时间(UTC)")
