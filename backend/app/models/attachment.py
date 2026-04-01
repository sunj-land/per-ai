from typing import Optional
from datetime import datetime
from sqlmodel import Field, SQLModel

class AttachmentBase(SQLModel):
    """
    附件基础模型
    """
    uuid: str = Field(index=True, unique=True, nullable=False, description="附件全局唯一标识符(UUID)，必填项，支持索引")
    original_name: str = Field(nullable=False, description="附件的原始文件名，必填项")
    ext: str = Field(nullable=False, description="附件的文件扩展名(如.pdf, .jpg)，必填项")
    size: int = Field(nullable=False, description="附件的文件大小，单位为字节(Bytes)，必填项")
    mime_type: str = Field(nullable=False, description="附件的MIME类型(如image/jpeg)，必填项")
    user_id: int = Field(nullable=False, foreign_key="user.id", description="上传该附件的用户ID，外键关联user表，必填项")
    channel_id: Optional[int] = Field(default=None, description="关联的渠道ID(如果附件属于特定渠道消息)，非必填")
    session_id: Optional[str] = Field(default=None, description="关联的聊天会话ID，非必填")
    file_hash: Optional[str] = Field(default=None, index=True, description="文件内容的哈希值(如MD5)，用于去重")
    is_deleted: bool = Field(default=False, description="逻辑删除标记，布尔值，默认False(未删除)")

class Attachment(AttachmentBase, table=True):
    """
    附件数据库表模型
    """
    id: Optional[int] = Field(default=None, primary_key=True, description="附件记录自增主键ID")
    local_path: str = Field(nullable=False, description="附件在服务器内部的实际存储路径，必填项")

    # 分享设置
    share_code: Optional[str] = Field(default=None, description="分享提取码，非必填")
    share_expiry: Optional[datetime] = Field(default=None, description="分享链接的过期时间，非必填")
    share_password: Optional[str] = Field(default=None, description="分享链接的访问密码，非必填")

    # 时间戳
    created_at: datetime = Field(default_factory=datetime.utcnow, description="附件上传/创建时间(UTC)，默认当前时间")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="附件最后更新时间(UTC)，默认当前时间")
    deleted_at: Optional[datetime] = Field(default=None, description="附件逻辑删除的具体时间，非必填")

class AttachmentCreate(SQLModel):
    """
    内部上传附件后用于创建记录的请求模型
    """
    uuid: str = Field(description="生成的唯一UUID")
    original_name: str = Field(description="原始文件名")
    ext: str = Field(description="扩展名")
    size: int = Field(description="文件大小(Bytes)")
    mime_type: str = Field(description="MIME类型")
    local_path: str = Field(description="本地存储路径")
    user_id: int = Field(description="上传用户ID")
    channel_id: Optional[int] = Field(default=None, description="关联的渠道ID")
    session_id: Optional[str] = Field(default=None, description="关联的聊天会话ID")
    file_hash: Optional[str] = Field(default=None, description="文件哈希值")

class AttachmentRead(AttachmentBase):
    """
    读取附件信息时的响应模型
    """
    id: int = Field(description="附件ID")
    created_at: datetime = Field(description="创建时间")
    updated_at: datetime = Field(description="更新时间")
    url: Optional[str] = Field(default=None, description="附件的公网可访问URL")
    preview_url: Optional[str] = Field(default=None, description="附件的缩略图或预览URL")

class AttachmentUpdate(SQLModel):
    """
    更新附件信息时的请求模型
    """
    is_deleted: Optional[bool] = Field(default=None, description="更新的逻辑删除状态")
    deleted_at: Optional[datetime] = Field(default=None, description="更新的逻辑删除时间")
    share_code: Optional[str] = Field(default=None, description="更新的分享提取码")
    share_expiry: Optional[datetime] = Field(default=None, description="更新的分享过期时间")
    share_password: Optional[str] = Field(default=None, description="更新的分享密码")
