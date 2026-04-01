from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship

class ArticleNoteBase(SQLModel):
    """
    文章笔记基础模型
    用于存储用户在阅读RSS文章时产生的高亮标注和笔记
    """
    article_id: int = Field(foreign_key="rssarticle.id", index=True, description="关联的RSS文章ID，外键关联rssarticle表，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="创建笔记的用户ID，外键关联user表，非必填")
    selected_text: str = Field(description="用户选中的原文高亮内容，必填项")
    start_offset: int = Field(default=0, description="选中文本在文章正文中的起始字符位置偏移量，默认0")
    end_offset: int = Field(default=0, description="选中文本在文章正文中的结束字符位置偏移量，默认0")
    color: str = Field(default="yellow", description="高亮标记颜色，默认为黄色(yellow)，可选值: yellow, red, green, blue")
    content: Optional[str] = Field(default=None, description="用户针对该高亮段落填写的笔记内容，非必填")
    tags: Optional[str] = Field(default=None, description="笔记的分类标签，多个标签以逗号分隔，非必填")
    importance: int = Field(default=1, description="笔记的重要程度等级，取值范围1-5，默认为1")

class ArticleNote(ArticleNoteBase, table=True):
    """
    文章笔记数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="笔记主键ID，自增")
    created_at: datetime = Field(default_factory=datetime.now, description="笔记创建时间，默认为当前时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="笔记最后更新时间，默认为当前时间")

class ArticleNoteCreate(ArticleNoteBase):
    """
    创建文章笔记时的请求模型
    """
    pass

class ArticleNoteRead(ArticleNoteBase):
    """
    读取文章笔记时的响应模型
    """
    id: int = Field(description="笔记ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

class ArticleNoteUpdate(SQLModel):
    """
    更新文章笔记时的请求模型
    """
    selected_text: Optional[str] = Field(default=None, description="更新的选中原文")
    start_offset: Optional[int] = Field(default=None, description="更新的起始偏移量")
    end_offset: Optional[int] = Field(default=None, description="更新的结束偏移量")
    color: Optional[str] = Field(default=None, description="更新的高亮颜色")
    content: Optional[str] = Field(default=None, description="更新的笔记内容")
    tags: Optional[str] = Field(default=None, description="更新的标签")
    importance: Optional[int] = Field(default=None, description="更新的重要性")


class ArticleSummaryBase(SQLModel):
    """
    文章总结基础模型
    用于存储系统或用户针对单篇文章生成的总结内容
    """
    article_id: int = Field(foreign_key="rssarticle.id", index=True, description="关联的RSS文章ID，外键关联rssarticle表，必填项")
    user_id: Optional[int] = Field(default=None, foreign_key="user.id", description="所属用户ID，外键关联user表，非必填")
    content: str = Field(description="文章的总结内容正文，支持HTML或Markdown格式，必填项")
    is_draft: bool = Field(default=False, description="是否为草稿状态，布尔值，默认False(否)")
    version: int = Field(default=1, description="总结内容的版本号，默认从1开始")

class ArticleSummary(ArticleSummaryBase, table=True):
    """
    文章总结数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="总结记录的主键ID，自增")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间，默认为当前时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="最后更新时间，默认为当前时间")
    is_vectorized: bool = Field(default=False, description="总结内容是否已进行向量化处理以便检索，布尔值，默认False(否)")

class ArticleSummaryCreate(ArticleSummaryBase):
    """
    创建文章总结时的请求模型
    """
    pass

class ArticleSummaryRead(ArticleSummaryBase):
    """
    读取文章总结时的响应模型
    """
    id: int = Field(description="总结ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")

class ArticleSummaryUpdate(SQLModel):
    """
    更新文章总结时的请求模型
    """
    content: Optional[str] = Field(default=None, description="更新的总结内容")
    is_draft: Optional[bool] = Field(default=None, description="更新的草稿状态")
    version: Optional[int] = Field(default=None, description="更新的版本号")
