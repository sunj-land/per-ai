from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from enum import Enum

class CardStatus(str, Enum):
    """
    卡片状态枚举类
    """
    DRAFT = "draft"          # 草稿状态
    PUBLISHED = "published"  # 已发布状态
    ARCHIVED = "archived"    # 已归档状态

class CardBase(SQLModel):
    """
    UI卡片基础模型
    """
    name: str = Field(index=True, unique=True, description="卡片系统名称，必填且唯一，用于代码或配置中引用")
    type: str = Field(default="custom", description="卡片类型，默认为'custom'(自定义)，可扩展其他内置类型")
    description: Optional[str] = Field(default=None, description="卡片用途和功能的详细描述，非必填")
    status: CardStatus = Field(default=CardStatus.DRAFT, description="卡片当前生命周期状态，默认值为草稿(draft)")
    
class Card(CardBase, table=True):
    """
    UI卡片数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="卡片自增主键ID")
    version: int = Field(default=1, description="当前卡片的最新主版本号，默认从1开始")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="卡片首次创建时间(UTC)")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="卡片最后修改时间(UTC)")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建该卡片的用户ID，外键关联user表")
    
    # 关联关系：一张卡片拥有多个版本历史记录
    versions: List["CardVersion"] = Relationship(back_populates="card")

class CardCreate(CardBase):
    """
    创建卡片时的请求模型
    """
    pass

class CardUpdate(SQLModel):
    """
    更新卡片时的请求模型
    """
    name: Optional[str] = Field(default=None, description="更新的卡片名称")
    type: Optional[str] = Field(default=None, description="更新的卡片类型")
    description: Optional[str] = Field(default=None, description="更新的卡片描述")
    status: Optional[CardStatus] = Field(default=None, description="更新的卡片状态")

class CardVersionBase(SQLModel):
    """
    卡片版本记录基础模型
    """
    version: int = Field(description="该记录对应的具体版本号，必填")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="提交该版本的用户ID，外键关联user表")
    code: str = Field(description="卡片的UI代码内容(如React/Vue代码字符串)，必填")
    config: Optional[str] = Field(default=None, description="卡片属性配置的JSON字符串(Props/Schema)，非必填")
    changelog: Optional[str] = Field(default=None, description="当前版本的更新日志说明，非必填")

class CardVersion(CardVersionBase, table=True):
    """
    卡片版本记录数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="版本记录自增主键ID")
    card_id: int = Field(foreign_key="card.id", description="所属卡片的ID，外键关联card表")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="该版本的创建/提交时间(UTC)")
    
    # 关联关系：所属卡片
    card: Optional[Card] = Relationship(back_populates="versions")

class CardVersionCreate(CardVersionBase):
    """
    创建新卡片版本时的请求模型
    """
    pass
