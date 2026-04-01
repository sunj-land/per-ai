import os
import uuid
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select
from fastapi import UploadFile, BackgroundTasks
from app.models.attachment import Attachment
from app.services.storage_service import storage_service
from app.services.file_processor import file_processor
from app.core.database import engine

class AttachmentService:
    """
    附件服务类，提供附件的上传、存储、异步处理、查询和删除等核心业务逻辑。
    """
    async def create_attachment(
        self,
        session: Session,
        file: UploadFile,
        user_id: int,
        channel_id: Optional[int] = None,
        session_id: Optional[str] = None,
        background_tasks: BackgroundTasks = None
    ) -> Attachment:
        """
        创建并存储新附件记录，支持触发后台异步处理。
        包含文件去重和安全校验。

        :param session: 数据库会话对象。
        :param file: 用户上传的文件对象 (FastAPI UploadFile)。
        :param user_id: 上传者的用户 ID。
        :param channel_id: 关联的频道 ID (可选)。
        :param session_id: 关联的会话 ID (可选)。
        :param background_tasks: FastAPI 的后台任务管理器 (可选)。
        :return: 创建成功的附件对象。
        """
        import hashlib
        import logging
        logger = logging.getLogger(__name__)

        # ========== 步骤0：安全校验（基础扩展名和 MIME 检查） ==========
        ext = os.path.splitext(file.filename)[1].lower()
        blocked_exts = {'.exe', '.sh', '.bat', '.cmd', '.msi', '.vbs'}
        if ext in blocked_exts:
            raise ValueError(f"Blocked file extension: {ext}")

        # ========== 步骤1：计算文件哈希以实现去重 ==========
        file_content = await file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        await file.seek(0) # Reset pointer

        # 查找是否存在相同哈希的文件
        existing_attachment = session.exec(
            select(Attachment).where(Attachment.file_hash == file_hash).where(Attachment.is_deleted == False)
        ).first()

        file_uuid = str(uuid.uuid4())

        if existing_attachment:
            logger.info(f"File deduplication: reusing existing file for hash {file_hash}")
            relative_path = existing_attachment.local_path
            absolute_path = storage_service.get_absolute_path(relative_path)
            mime_type = existing_attachment.mime_type
            size = existing_attachment.size
        else:
            # 将文件保存到存储服务，并获取相对路径与绝对路径
            relative_path, absolute_path = await storage_service.save_file(file, file_uuid, ext)
            # 获取 MIME 类型
            mime_type = file_processor.get_mime_type(absolute_path)
            size = os.path.getsize(absolute_path)

        # ========== 步骤2：创建数据库记录 ==========
        attachment = Attachment(
            uuid=file_uuid,
            original_name=file.filename,
            ext=ext,
            size=size,
            mime_type=mime_type,
            local_path=relative_path,
            user_id=user_id,
            channel_id=channel_id,
            session_id=session_id,
            file_hash=file_hash
        )
        session.add(attachment)
        session.commit()
        session.refresh(attachment)

        logger.info(f"Attachment created: {attachment.uuid} by user {user_id}")

        # ========== 步骤3：触发后台异步任务（如果需要） ==========
        # 如果传入了后台任务管理器且是新文件，则添加文件处理任务（如病毒扫描等）
        if background_tasks and not existing_attachment:
            background_tasks.add_task(self.process_file, attachment.id, absolute_path)

        return attachment

    async def process_file(self, attachment_id: int, file_path: str):
        """
        后台处理文件的异步任务，包括病毒扫描、缩略图生成和格式转换等操作。

        :param attachment_id: 附件记录的 ID。
        :param file_path: 文件在本地服务器的绝对路径。
        """
        with Session(engine) as session:
            attachment = session.get(Attachment, attachment_id)
            if not attachment:
                return

            # ========== 1. 病毒扫描 ==========
            is_safe = file_processor.scan_virus(file_path)
            if not is_safe:
                # 若文件不安全，则标记为已删除或隔离
                attachment.is_deleted = True
                attachment.deleted_at = datetime.utcnow()
                session.add(attachment)
                session.commit()
                # 也可以选择立即删除本地文件
                storage_service.delete_file(attachment.local_path)
                return

            # ========== 2. 缩略图生成与 PDF 转换（备用逻辑） ==========
            # 后续可用于更新元数据或创建派生文件。
            # 目前 MVP 阶段可能暂不生成，或者根据需求进行扩展。
            pass

    def get_attachment_by_uuid(self, session: Session, uuid: str) -> Optional[Attachment]:
        """
        根据 UUID 查找指定的附件记录。

        :param session: 数据库会话对象。
        :param uuid: 附件的 UUID 字符串。
        :return: 查找到的附件对象，若不存在则返回 None。
        """
        statement = select(Attachment).where(Attachment.uuid == uuid)
        return session.exec(statement).first()

    def delete_attachment(self, session: Session, uuid: str):
        """
        软删除指定的附件记录。

        :param session: 数据库会话对象。
        :param uuid: 附件的 UUID 字符串。
        """
        attachment = self.get_attachment_by_uuid(session, uuid)
        if attachment:
            # 标记为已删除，并记录删除时间
            attachment.is_deleted = True
            attachment.deleted_at = datetime.utcnow()
            session.add(attachment)
            session.commit()

    def search_attachments(
        self,
        session: Session,
        keyword: Optional[str] = None,
        mime_type: Optional[str] = None,
        channel_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Attachment]:
        """
        查询并搜索附件记录，支持多条件筛选。

        :param session: 数据库会话对象。
        :param keyword: 按原始文件名进行模糊匹配的关键字。
        :param mime_type: 按文件 MIME 类型过滤。
        :param channel_id: 关联的频道 ID。
        :param user_id: 上传者的用户 ID。
        :param limit: 最大返回条数，默认为 20。
        :param offset: 分页偏移量，默认为 0。
        :return: 符合条件的附件记录列表。
        """
        # 仅查询未被软删除的附件
        statement = select(Attachment).where(Attachment.is_deleted == False)

        # 动态添加过滤条件
        if keyword:
            statement = statement.where(Attachment.original_name.contains(keyword))
        if mime_type:
            statement = statement.where(Attachment.mime_type.startswith(mime_type))
        if channel_id:
            statement = statement.where(Attachment.channel_id == channel_id)
        if user_id:
            statement = statement.where(Attachment.user_id == user_id)

        # 按创建时间倒序排列并应用分页
        statement = statement.order_by(Attachment.created_at.desc()).offset(offset).limit(limit)
        return session.exec(statement).all()

attachment_service = AttachmentService()
