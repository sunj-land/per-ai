from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Body
from pydantic import BaseModel
from app.models.channel import Channel, ChannelCreate, ChannelUpdate, ChannelMessage
from app.core.dependencies import get_channel_service
from app.services.protocols import ChannelServiceProtocol

router = APIRouter()


class ChannelMessagePagination(BaseModel):
    total: int
    items: List[ChannelMessage]


@router.get("/messages", response_model=ChannelMessagePagination)
async def get_messages(
    skip: int = 0,
    limit: int = 100,
    channel_id: Optional[UUID] = None,
    keyword: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[str] = None,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return svc.get_messages(
        skip=skip, limit=limit, channel_id=channel_id,
        keyword=keyword, start_date=start_date, end_date=end_date, status=status,
    )


@router.post("/", response_model=Channel)
async def create_channel(
    channel: ChannelCreate,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return svc.create_channel(channel)


@router.get("/", response_model=List[Channel])
async def get_channels(
    skip: int = 0,
    limit: int = 100,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return svc.get_channels(skip, limit)


@router.get("/{channel_id}", response_model=Channel)
async def get_channel(
    channel_id: UUID,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    channel = svc.get_channel(channel_id)
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    return channel


@router.put("/{channel_id}", response_model=Channel)
async def update_channel(
    channel_id: UUID,
    channel: ChannelUpdate,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    updated = svc.update_channel(channel_id, channel)
    if not updated:
        raise HTTPException(status_code=404, detail="Channel not found")
    return updated


@router.delete("/{channel_id}", response_model=bool)
async def delete_channel(
    channel_id: UUID,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    success = svc.delete_channel(channel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Channel not found")
    return True


@router.get("/{channel_id}/messages", response_model=List[ChannelMessage])
async def get_channel_messages(
    channel_id: UUID,
    skip: int = 0,
    limit: int = 100,
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return svc.get_channel_messages(channel_id, skip, limit)


@router.post("/{channel_id}/webhook")
async def handle_webhook(
    channel_id: UUID,
    payload: dict = Body(...),
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return await svc.handle_webhook(channel_id, payload)


@router.post("/{channel_id}/send", response_model=ChannelMessage)
async def send_message(
    channel_id: UUID,
    content: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    try:
        return await svc.send_message(channel_id, content, title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast", response_model=List[ChannelMessage])
async def broadcast_message(
    content: str = Body(..., embed=True),
    title: Optional[str] = Body(None, embed=True),
    svc: ChannelServiceProtocol = Depends(get_channel_service),
):
    return await svc.broadcast(content, title)
