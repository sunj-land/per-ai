import json
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import StreamingResponse
from sqlmodel import Session
from app.core.database import get_session
from app.core.dependencies import get_chat_service
from app.services.protocols import ChatServiceProtocol
from app.models.chat import ChatSession, ChatMessage, ChatSessionRead, ChatMessageRead
import uuid
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import asyncio
from fastapi import Request

# 创建 API 路由
router = APIRouter()

class ChatMessageRequest(BaseModel):
    """
    发送聊天消息的请求模型。
    """
    content: str  # 消息内容
    model_id: str  # 使用的模型 ID
    images: Optional[List[str]] = None  # 可选的图片列表（Base64 或 URL）
    attachments: Optional[List[str]] = None  # 可选的附件 UUID 列表
    extra: Optional[dict] = None  # 额外的元数据（如来源、配置等）

class ChatSessionUpdate(BaseModel):
    """
    更新聊天会话的请求模型。
    """
    title: str  # 新的会话标题

@router.post("/sessions", response_model=ChatSessionRead, summary="Create a new chat session")
def create_session(session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    创建一个新的聊天会话。

    Args:
        session (Session): 数据库会话依赖。

    Returns:
        ChatSessionRead: 创建的会话信息。
    """
    return svc.create_session(session)

@router.get("/sessions", response_model=List[ChatSessionRead], summary="List chat sessions with optional search")
def get_sessions(
    limit: int = 20,
    offset: int = 0,
    query: Optional[str] = Query(None, description="Search keyword in title or messages"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    session: Session = Depends(get_session),
    svc: ChatServiceProtocol = Depends(get_chat_service),
):
    """
    获取聊天会话列表，支持分页和搜索。

    Args:
        limit (int): 每页数量，默认为 20。
        offset (int): 偏移量，默认为 0。
        query (Optional[str]): 搜索关键词（匹配标题或消息内容）。
        start_date (Optional[datetime]): 过滤起始日期。
        end_date (Optional[datetime]): 过滤结束日期。
        session (Session): 数据库会话依赖。

    Returns:
        List[ChatSessionRead]: 会话列表。
    """
    return svc.get_sessions(session, limit, offset, query, start_date, end_date)

@router.get("/qqbot-session", response_model=ChatSessionRead, summary="Get or create fixed QQBot session")
def get_qqbot_session(session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    获取或创建固定的 QQBot 协同会话。
    该会话用于与 QQ 机器人进行交互。

    Args:
        session (Session): 数据库会话依赖。

    Returns:
        ChatSessionRead: QQBot 会话信息。
    """
    return svc.get_or_create_qqbot_session(session)

@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageRead], summary="Get messages for a session")
def get_messages(session_id: uuid.UUID, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    获取指定会话的所有消息。

    Args:
        session_id (uuid.UUID): 会话 ID。
        session (Session): 数据库会话依赖。

    Returns:
        List[ChatMessageRead]: 消息列表。
    """
    return svc.get_messages(session, session_id)

@router.post("/sessions/{session_id}/send", summary="Send a message to the chat session")
async def send_message(
    session_id: uuid.UUID,
    request: ChatMessageRequest,
    session: Session = Depends(get_session),
    svc: ChatServiceProtocol = Depends(get_chat_service),
):
    """
    向指定会话发送消息，并以流式响应返回 AI 的回复。

    Args:
        session_id (uuid.UUID): 会话 ID。
        request (ChatMessageRequest): 消息请求体。
        session (Session): 数据库会话依赖。

    Returns:
        StreamingResponse: 流式响应，包含 AI 生成的内容（NDJSON 格式）。
    """
    extra = request.extra or {}
    if "from" not in extra:
        extra["from"] = "web"

    # 直接调用 svc 的 send_message 获取流式响应
    stream = svc.send_message(
        session=session,
        session_id=session_id,
        content=request.content,
        model_id=request.model_id,
        images=request.images,
        attachments=request.attachments,
        extra=extra
    )

    return StreamingResponse(
        stream,
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache, no-store",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )

@router.get("/sessions/{session_id}/events", summary="SSE endpoint for session events")
async def session_events(session_id: uuid.UUID, request: Request, svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    SSE (Server-Sent Events) 端点，用于订阅会话事件。
    客户端可以通过此端点实时接收新消息通知。

    Args:
        session_id (uuid.UUID): 会话 ID。
        request (Request): FastAPI 请求对象，用于检测断开连接。

    Returns:
        StreamingResponse: SSE 流式响应。
    """
    # 订阅该会话的事件队列
    q = svc.subscribe(str(session_id))

    async def event_generator():
        try:
            while True:
                # 检查客户端是否已断开连接
                if await request.is_disconnected():
                    break
                # 等待并获取队列中的事件
                event_data = await q.get()
                # 生成 SSE 格式的数据
                yield f"data: {json.dumps(event_data)}\n\n"
        finally:
            # 客户端断开或发生异常时，取消订阅
            svc.unsubscribe(str(session_id), q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/models", summary="List enabled models")
async def list_models(svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    获取所有启用的 AI 模型列表。

    Returns:
        List[dict]: 模型配置列表。
    """
    return await svc.get_enabled_models()

@router.delete("/sessions/{session_id}", summary="Delete a chat session")
def delete_session(session_id: uuid.UUID, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    删除指定的聊天会话。

    Args:
        session_id (uuid.UUID): 会话 ID。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果会话不存在 (404)。

    Returns:
        dict: 操作结果消息。
    """
    success = svc.delete_session(session, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}

@router.patch("/sessions/{session_id}", response_model=ChatSessionRead, summary="Update session title")
def update_session(session_id: uuid.UUID, update: ChatSessionUpdate, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    更新会话标题。

    Args:
        session_id (uuid.UUID): 会话 ID。
        update (ChatSessionUpdate): 更新内容。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果会话不存在 (404)。

    Returns:
        ChatSessionRead: 更新后的会话信息。
    """
    updated_session = svc.update_session_title(session, session_id, update.title)
    if not updated_session:
        raise HTTPException(status_code=404, detail="Session not found")
    return updated_session

class ChatMessageFeedbackRequest(BaseModel):
    """
    消息反馈请求模型。
    """
    feedback: Optional[str] = None # "like" (点赞) or "dislike" (点踩) or None (取消)

class ChatMessageFavoriteRequest(BaseModel):
    """
    消息收藏请求模型。
    """
    is_favorite: bool # 是否收藏

@router.post("/messages/{message_id}/feedback", summary="Update message feedback")
def update_feedback(message_id: uuid.UUID, request: ChatMessageFeedbackRequest, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    更新消息的反馈状态（点赞/点踩）。

    Args:
        message_id (uuid.UUID): 消息 ID。
        request (ChatMessageFeedbackRequest): 反馈内容。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果消息不存在 (404)。

    Returns:
        dict: 操作结果消息。
    """
    msg = svc.update_message_feedback(session, message_id, request.feedback)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Feedback updated"}

@router.post("/messages/{message_id}/favorite", summary="Update message favorite status")
def update_favorite(message_id: uuid.UUID, request: ChatMessageFavoriteRequest, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    更新消息的收藏状态。

    Args:
        message_id (uuid.UUID): 消息 ID。
        request (ChatMessageFavoriteRequest): 收藏状态。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果消息不存在 (404)。

    Returns:
        dict: 操作结果消息。
    """
    msg = svc.update_message_favorite(session, message_id, request.is_favorite)
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return {"message": "Favorite updated"}

@router.post("/sessions/{session_id}/share", summary="Generate share link for a session")
def share_session(session_id: uuid.UUID, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    为会话生成分享链接 ID。

    Args:
        session_id (uuid.UUID): 会话 ID。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果会话不存在 (404)。

    Returns:
        dict: 包含 share_id 的字典。
    """
    share_id = svc.share_session(session, session_id)
    if not share_id:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"share_id": share_id}

@router.get("/shared/{share_id}", summary="Get shared session")
def get_shared_session(share_id: str, session: Session = Depends(get_session), svc: ChatServiceProtocol = Depends(get_chat_service)):
    """
    获取分享的会话内容。

    Args:
        share_id (str): 分享 ID。
        session (Session): 数据库会话依赖。

    Raises:
        HTTPException: 如果分享链接无效或会话不存在 (404)。

    Returns:
        dict: 包含会话信息和消息列表。
    """
    data = svc.get_shared_session(session, share_id)
    if not data:
        raise HTTPException(status_code=404, detail="Shared session not found")
    return data
