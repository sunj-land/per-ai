from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, String, JSON, Integer
from enum import Enum

# 避免循环引用
if TYPE_CHECKING:
    pass

# ========== 枚举定义 ==========
class UserStatus(str, Enum):
    """
    用户状态枚举
    """
    ACTIVE = "active"       # 正常
    LOCKED = "locked"       # 锁定
    DISABLED = "disabled"   # 禁用

class LoginStatus(str, Enum):
    """
    登录状态枚举
    """
    SUCCESS = "success"     # 成功
    FAILURE = "failure"     # 失败

# ========== 关联表模型 ==========
class UserRoleLink(SQLModel, table=True):
    """
    用户-角色关联表 (多对多)
    """
    __tablename__ = "user_role_link"

    user_id: Optional[int] = Field(default=None, foreign_key="user.id", primary_key=True, description="关联的用户ID，联合主键，外键指向user表") # 用户ID
    role_id: Optional[int] = Field(default=None, foreign_key="role.id", primary_key=True, description="关联的角色ID，联合主键，外键指向role表") # 角色ID

# ========== 角色模型 ==========
class Role(SQLModel, table=True):
    """
    角色表
    """
    __tablename__ = "role"

    id: Optional[int] = Field(default=None, primary_key=True, description="角色记录全局唯一ID，主键") # 角色ID
    name: str = Field(index=True, unique=True, max_length=50, description="角色名称，必填项，要求唯一且最长50字符") # 角色名称
    description: Optional[str] = Field(default=None, max_length=255, description="角色描述，可选项，最长255字符") # 角色描述
    permissions: List[str] = Field(default=[], sa_column=Column(JSON), description="权限标识集合，默认空列表，以JSON格式存储") # 权限标识集合

    # 关系
    users: List["User"] = Relationship(back_populates="roles", link_model=UserRoleLink)

# ========== 用户模型 ==========
class User(SQLModel, table=True):
    """
    用户表
    """
    __tablename__ = "user"

    id: Optional[int] = Field(default=None, primary_key=True, description="用户记录全局唯一ID，主键") # 用户ID
    username: str = Field(index=True, unique=True, max_length=50, description="用户名，必填项，要求唯一且最长50字符") # 用户名
    email: Optional[str] = Field(default=None, index=True, max_length=100, description="用户电子邮箱，可选项，要求唯一且最长100字符") # 邮箱
    phone: Optional[str] = Field(default=None, index=True, max_length=20, description="用户手机号码，可选项，要求唯一且最长20字符") # 手机号
    hashed_password: str = Field(max_length=255, description="密码哈希值，必填项，用于安全验证") # 密码哈希
    salt: Optional[str] = Field(default=None, max_length=255, description="密码盐值，可选项，配合哈希密码增强安全性") # 盐值 (bcrypt自带盐，此字段可作为额外安全混淆或备用)
    role: str = Field(default="user", description="用户主角色标识，默认值为'user'") # 兼容旧字段 (role column exists in DB)
    role_id: Optional[int] = Field(default=None, foreign_key="role.id", description="关联的主角色ID，可选项，外键指向role表") # 主角色ID (冗余字段，便于快速查询)
    status: UserStatus = Field(default=UserStatus.ACTIVE, description="用户状态枚举，默认值为正常(ACTIVE)") # 状态
    is_active: bool = Field(default=True, description="是否处于活跃状态，默认值为True") # 兼容旧字段

    # 安全字段
    failed_login_count: int = Field(default=0, description="连续登录失败次数，默认值为0") # 登录失败次数
    locked_until: Optional[datetime] = Field(default=None, description="账户锁定截止时间，可选项") # 锁定截止时间
    reset_token: Optional[str] = Field(default=None, max_length=255, description="密码重置令牌，可选项，用于找回密码流程") # 重置令牌
    reset_token_expires_at: Optional[datetime] = Field(default=None, description="密码重置令牌过期时间，可选项") # 重置令牌过期时间

    # 扩展字段
    extension_json: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="扩展JSON字段，可选项，用于存储动态扩展属性") # 扩展JSON字段
    ext_1: Optional[str] = Field(default=None, max_length=255, description="备用扩展字符串1，可选项") # 备用字符串1
    ext_2: Optional[str] = Field(default=None, max_length=255, description="备用扩展字符串2，可选项") # 备用字符串2
    ext_3: Optional[str] = Field(default=None, max_length=255, description="备用扩展字符串3，可选项") # 备用字符串3
    int_1: Optional[int] = Field(default=None, description="备用扩展整数1，可选项") # 备用整数1
    int_2: Optional[int] = Field(default=None, description="备用扩展整数2，可选项") # 备用整数2
    int_3: Optional[int] = Field(default=None, description="备用扩展整数3，可选项") # 备用整数3

    created_at: datetime = Field(default_factory=datetime.utcnow, description="用户记录创建时间，默认自动生成当前UTC时间") # 创建时间
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="用户记录更新时间，默认自动生成当前UTC时间") # 更新时间

    # 关系
    roles: List[Role] = Relationship(back_populates="users", link_model=UserRoleLink)
    login_logs: List["LoginLog"] = Relationship(back_populates="user")

# ========== 登录日志模型 ==========
class LoginLog(SQLModel, table=True):
    """
    登录日志表
    """
    __tablename__ = "login_log"

    id: Optional[int] = Field(default=None, primary_key=True, description="登录日志记录全局唯一ID，主键") # 日志ID
    user_id: int = Field(foreign_key="user.id", index=True, description="关联的用户ID，必填项，外键指向user表") # 用户ID
    login_time: datetime = Field(default_factory=datetime.utcnow, description="登录操作发生时间，默认自动生成当前UTC时间") # 登录时间
    ip_address: str = Field(max_length=50, description="登录时使用的IP地址，必填项") # 登录IP
    status: LoginStatus = Field(default=LoginStatus.SUCCESS, description="登录状态枚举，默认值为成功(SUCCESS)") # 登录状态
    failure_reason: Optional[str] = Field(default=None, max_length=255, description="登录失败的具体原因，可选项") # 失败原因
    user_agent: Optional[str] = Field(default=None, max_length=500, description="登录时客户端的User-Agent信息，可选项") # 用户代理信息

    # 关系
    user: User = Relationship(back_populates="login_logs")

# ========== Pydantic 模型 (用于 API 交互) ==========

class UserBase(SQLModel):
    """
    用户基础模型
    用于API请求的公共字段
    """
    username: str = Field(description="用户名，必填项")
    email: Optional[str] = Field(default=None, description="电子邮箱，可选项")
    phone: Optional[str] = Field(default=None, description="手机号码，可选项")
    full_name: Optional[str] = Field(default=None, description="全名，可选项") # 兼容旧代码

class UserCreate(UserBase):
    """
    创建用户请求模型
    """
    password: str = Field(description="明文密码，必填项，后端将进行哈希处理")
    role_ids: List[int] = Field(default=[], description="角色ID列表，可选项，指定用户拥有的角色")

class UserRead(UserBase):
    """
    读取用户响应模型
    """
    id: int = Field(description="用户ID")
    status: UserStatus = Field(description="用户当前状态")
    roles: List[Role] = Field(default=[], description="用户拥有的角色列表")
    created_at: datetime = Field(description="用户创建时间")

class UserUpdate(SQLModel):
    """
    更新用户请求模型
    """
    email: Optional[str] = Field(default=None, description="新的电子邮箱")
    phone: Optional[str] = Field(default=None, description="新的手机号码")
    full_name: Optional[str] = Field(default=None, description="新的全名")
    password: Optional[str] = Field(default=None, description="新的明文密码")
    status: Optional[UserStatus] = Field(default=None, description="新的用户状态")
    role_ids: Optional[List[int]] = Field(default=None, description="新的角色ID列表")

class UserListResponse(SQLModel):
    """
    用户列表分页响应模型
    """
    items: List[UserRead] = Field(description="用户列表数据")
    total: int = Field(description="用户总数")
