from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select, func
from typing import Optional, List
import os
from app.core.database import get_session
from app.core.dependencies import get_attachment_service, get_storage_service
from app.models.attachment import Attachment, AttachmentRead, AttachmentUpdate
from app.models.user import User
from app.core.auth import get_current_user

router = APIRouter()

@router.post("/upload", response_model=AttachmentRead, summary="Upload a file and create an attachment")
async def upload_attachment(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    channel_id: Optional[int] = Form(None),
    session_id: Optional[str] = Form(None),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    svc=Depends(get_attachment_service),
):
    """
    上传文件并创建附件记录，支持去重和异步扫描。
    """
    if not file:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail="No file provided")

    try:
        attachment = await svc.create_attachment(
            session=session,
            file=file,
            user_id=current_user.id,
            channel_id=channel_id,
            session_id=session_id,
            background_tasks=background_tasks
        )
        return attachment
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to upload file")

@router.get("/list", response_model=dict, summary="List attachments with pagination and filters")
async def list_attachments(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    channel_id: Optional[int] = Query(None, description="Filter by channel ID"),
    keyword: Optional[str] = Query(None, description="Filter by original filename"),
    mime_type: Optional[str] = Query(None, description="Filter by MIME type"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Items per page"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    获取附件列表，支持分页和多维度检索。
    """
    query = select(Attachment).where(Attachment.user_id == current_user.id, Attachment.is_deleted == False)

    if session_id:
        query = query.where(Attachment.session_id == session_id)
    if channel_id:
        query = query.where(Attachment.channel_id == channel_id)
    if keyword:
        query = query.where(Attachment.original_name.contains(keyword))
    if mime_type:
        query = query.where(Attachment.mime_type.contains(mime_type))

    total_query = select(func.count()).select_from(query.subquery())
    total = session.exec(total_query).one()

    offset = (page - 1) * size
    query = query.order_by(Attachment.created_at.desc()).offset(offset).limit(size)
    attachments = session.exec(query).all()

    return {"items": attachments, "total": total, "page": page, "size": size}

@router.get("/search", response_model=List[AttachmentRead])
async def search_attachments(
    keyword: Optional[str] = None,
    mime_type: Optional[str] = None,
    channel_id: Optional[int] = None,
    limit: int = 20,
    offset: int = 0,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    svc=Depends(get_attachment_service),
):
    """
    搜索和筛选附件。
    """
    return svc.search_attachments(session, keyword, mime_type, channel_id, limit=limit, offset=offset)

@router.get("/{uuid}", response_model=AttachmentRead, summary="Get attachment metadata")
async def get_attachment(
    uuid: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    svc=Depends(get_attachment_service),
):
    """
    获取附件元数据。
    """
    attachment = svc.get_attachment_by_uuid(session, uuid)
    if not attachment or attachment.is_deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if attachment.user_id != current_user.id and not attachment.channel_id and not attachment.session_id:
        pass  # Allow access if it's a public or specific channel

    return attachment

@router.get("/{uuid}/download")
async def download_attachment(
    uuid: str,
    session: Session = Depends(get_session),
    svc=Depends(get_attachment_service),
    storage=Depends(get_storage_service),
):
    """
    下载指定 UUID 的附件文件。
    """
    attachment = svc.get_attachment_by_uuid(session, uuid)
    if not attachment or attachment.is_deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = storage.get_absolute_path(attachment.local_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(file_path, media_type=attachment.mime_type, filename=attachment.original_name)

@router.get("/{uuid}/preview")
async def preview_attachment(
    uuid: str,
    session: Session = Depends(get_session),
    svc=Depends(get_attachment_service),
    storage=Depends(get_storage_service),
):
    """
    预览指定 UUID 的附件文件。支持直接预览图片、PDF，以及已转换的 Office 文档。
    """
    attachment = svc.get_attachment_by_uuid(session, uuid)
    if not attachment or attachment.is_deleted:
        raise HTTPException(status_code=404, detail="Attachment not found")

    file_path = storage.get_absolute_path(attachment.local_path)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    if attachment.mime_type and attachment.mime_type.startswith("image/"):
        return FileResponse(file_path, media_type=attachment.mime_type)

    if attachment.mime_type == "application/pdf":
        return FileResponse(file_path, media_type="application/pdf")

    base, _ = os.path.splitext(file_path)
    pdf_path = f"{base}.pdf"
    if os.path.exists(pdf_path):
        return FileResponse(pdf_path, media_type="application/pdf")

    raise HTTPException(status_code=404, detail="Preview not available (conversion pending or failed)")

@router.delete("/{uuid}")
async def delete_attachment(
    uuid: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
    svc=Depends(get_attachment_service),
):
    """
    删除指定的附件。
    """
    attachment = svc.get_attachment_by_uuid(session, uuid)
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    if attachment.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    svc.delete_attachment(session, uuid)
    return {"status": "ok"}

@router.post("/{uuid}/share")
async def share_attachment(
    uuid: str,
    password: Optional[str] = None,
    expiry_hours: int = 24,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    """
    分享附件，生成分享链接（待完善）。
    """
    pass
