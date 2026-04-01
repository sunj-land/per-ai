from datetime import datetime
from typing import Optional, List
from sqlmodel import Field, SQLModel, Relationship

# Forward references for relationships
class RSSFeedGroupLink(SQLModel, table=True):
    """
    RSS订阅源与分组的多对多关联表模型
    """
    feed_id: Optional[int] = Field(default=None, foreign_key="rssfeed.id", primary_key=True, description="关联的订阅源ID，联合主键")
    group_id: Optional[int] = Field(default=None, foreign_key="rssgroup.id", primary_key=True, description="关联的分组ID，联合主键")

class RSSGroupBase(SQLModel):
    """
    RSS分组基础模型
    """
    name: str = Field(index=True, unique=True, description="分组名称，必填且全局唯一")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建该分组的用户ID，外键关联user表，非必填")
    parent_id: Optional[int] = Field(default=None, foreign_key="rssgroup.id", description="父级分组ID，用于构建树形结构，外键关联自身，非必填")
    icon: Optional[str] = Field(default=None, description="分组对应的图标或Emoji，非必填")
    color: Optional[str] = Field(default=None, description="分组的颜色标识代码(如Hex)，非必填")
    order: int = Field(default=0, description="分组的展示排序权重，数字越小越靠前，默认0")

class RSSGroup(RSSGroupBase, table=True):
    """
    RSS分组数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="分组主键ID，自增")

    # 关联关系：自身层级关系与多对多订阅源关系
    children: List["RSSGroup"] = Relationship(sa_relationship_kwargs={"remote_side": "app.models.rss.RSSGroup.id"})
    feeds: List["RSSFeed"] = Relationship(back_populates="groups", link_model=RSSFeedGroupLink)

class RSSGroupCreate(RSSGroupBase):
    """创建 RSS 分组请求模型"""
    pass

class RSSGroupUpdate(SQLModel):
    """更新 RSS 分组请求模型"""
    name: Optional[str] = Field(default=None, description="更新的名称")
    parent_id: Optional[int] = Field(default=None, description="更新的父分组ID")
    icon: Optional[str] = Field(default=None, description="更新的图标")
    color: Optional[str] = Field(default=None, description="更新的颜色")
    order: Optional[int] = Field(default=None, description="更新的排序")

class RSSGroupRead(RSSGroupBase):
    """读取 RSS 分组响应模型"""
    id: int = Field(description="分组ID")
    feeds_count: int = Field(default=0, description="分组下包含的订阅源数量")
    children: Optional[List["RSSGroupRead"]] = Field(default=None, description="子分组列表")

class RSSFeedBase(SQLModel):
    """RSS 订阅源基础模型"""
    url: str = Field(index=True, unique=True, description="RSS源的XML链接地址，必填且全局唯一")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID，外键关联user表，非必填")
    title: Optional[str] = Field(default=None, description="抓取到的或用户自定义的订阅源标题，非必填")
    description: Optional[str] = Field(default=None, description="订阅源的描述信息，非必填")
    group_name: Optional[str] = Field(default=None, description="订阅源分组名称(已废弃，建议使用groups关联)，非必填")
    is_active: bool = Field(default=True, description="是否启用自动抓取，布尔值，默认True(启用)")
    is_whitelisted: bool = Field(default=False, description="是否被加入白名单(免于被自动清理保护)，布尔值，默认False(否)")

class RSSFeed(RSSFeedBase, table=True):
    """RSS 订阅源数据库表模型"""
    id: Optional[int] = Field(default=None, primary_key=True, description="订阅源主键ID，自增")
    last_fetched_at: Optional[datetime] = Field(default=None, description="最后一次成功抓取更新的时间戳，非必填")
    last_fetch_status: str = Field(default="pending", description="最后一次抓取任务的状态，默认为pending，可选值: success(成功), error(失败), pending(待抓取)")
    error_message: Optional[str] = Field(default=None, description="如果抓取失败，记录的详细错误信息，非必填")

    # 关联关系
    articles: List["RSSArticle"] = Relationship(back_populates="feed")
    groups: List["RSSGroup"] = Relationship(back_populates="feeds", link_model=RSSFeedGroupLink)

class RSSFeedCreate(RSSFeedBase):
    """创建 RSS 订阅源请求模型"""
    group_ids: Optional[List[int]] = Field(default=None, description="创建时关联的分组ID列表")

class RSSFeedUpdate(SQLModel):
    """更新 RSS 订阅源请求模型"""
    url: Optional[str] = Field(default=None, description="更新的URL")
    title: Optional[str] = Field(default=None, description="更新的标题")
    description: Optional[str] = Field(default=None, description="更新的描述")
    group_name: Optional[str] = Field(default=None, description="更新的废弃分组名")
    is_active: Optional[bool] = Field(default=None, description="更新的启用状态")
    is_whitelisted: Optional[bool] = Field(default=None, description="更新的白名单状态")
    group_ids: Optional[List[int]] = Field(default=None, description="更新的关联分组列表")

class RSSFeedRead(RSSFeedBase):
    """读取 RSS 订阅源响应模型"""
    id: int = Field(description="订阅源ID")
    last_fetched_at: Optional[datetime] = Field(default=None, description="最后一次成功抓取的时间")
    last_fetch_status: str = Field(default="pending", description="最后一次抓取状态")
    error_message: Optional[str] = Field(default=None, description="错误信息")
    articles_count: int = Field(default=0, description="该订阅源下入库的文章总数量")
    groups: Optional[List[RSSGroupRead]] = Field(default=None, description="所属分组列表")

class RSSArticleBase(SQLModel):
    """RSS 文章基础模型"""
    title: str = Field(description="文章的原始标题，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="归属的用户ID，非必填")
    link: str = Field(index=True, description="文章的原始访问链接，必填且建立索引")
    summary: Optional[str] = Field(default=None, description="文章的摘要内容或片段，非必填")
    content: Optional[str] = Field(default=None, description="文章的完整HTML或纯文本正文内容，非必填")
    published_at: Optional[datetime] = Field(default=None, description="文章的原始发布时间，非必填")
    author: Optional[str] = Field(default=None, description="文章的作者名称，非必填")
    category: Optional[str] = Field(default=None, description="文章的分类信息，非必填")
    enclosure_url: Optional[str] = Field(default=None, description="文章附带的多媒体附件链接(如播客音频)，非必填")
    enclosure_type: Optional[str] = Field(default=None, description="附件的MIME类型，非必填")
    content_hash: str = Field(index=True, description="基于文章内容计算的哈希值，用于重复检测和去重，必填且建立索引")
    is_read: bool = Field(default=False, description="用户是否已阅读过该文章，布尔值，默认False(未读)")
    is_starred: bool = Field(default=False, description="用户是否收藏了该文章，布尔值，默认False(未收藏)")
    is_vectorized: bool = Field(default=False, description="文章内容是否已向量化入库以便语义检索，布尔值，默认False(否)")

class RSSArticle(RSSArticleBase, table=True):
    """RSS 文章数据库表模型"""
    id: Optional[int] = Field(default=None, primary_key=True, description="文章记录主键ID，自增")
    feed_id: Optional[int] = Field(default=None, foreign_key="rssfeed.id", description="关联的订阅源ID，外键关联rssfeed表，非必填")

    # 关联关系
    feed: Optional[RSSFeed] = Relationship(back_populates="articles")

class RSSArticleRead(RSSArticleBase):
    """读取 RSS 文章响应模型"""
    id: int = Field(description="文章ID")
    feed_title: Optional[str] = Field(default=None, description="所属的订阅源标题名称，非必填")

class BatchDelete(SQLModel):
    """批量删除请求模型"""
    feed_ids: List[int] = Field(description="需要批量删除的订阅源ID列表")
