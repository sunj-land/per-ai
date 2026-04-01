from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.auth import get_current_active_user, User
from app.models.progress import (
    UserProgress, UserProgressBase, EventLog, EventLogBase, EventType
)

# 创建进度和事件日志相关的 API 路由
router = APIRouter()

@router.get("/", response_model=UserProgressBase, summary="获取当前用户的总体进度")
async def get_progress(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    获取当前用户的总体学习进度信息。如果用户尚未拥有进度记录，则自动初始化一条。

    Args:
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        UserProgressBase: 用户的进度汇总信息，如总学习时间等。
    """
    # 查找用户的进度记录
    progress = session.exec(select(UserProgress).where(UserProgress.user_id == current_user.id)).first()
    
    if not progress:
        # 如果未找到，则初始化用户的进度
        progress = UserProgress(user_id=current_user.id)
        session.add(progress)
        session.commit()
        session.refresh(progress)
        
    return progress

@router.post("/events", response_model=EventLog, summary="记录学习事件")
async def log_event(
    event_data: EventLogBase,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    记录用户的行为事件（如学习开始、学习结束等）。
    如果是完成事件 (FINISH)，则会自动累加事件的持续时间到用户的总学习时间中。

    Args:
        event_data (EventLogBase): 事件的数据负载，包含事件类型、持续时间等。
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        EventLog: 记录成功的事件对象。
    """
    # 创建事件记录
    event = EventLog.from_orm(event_data)
    event.user_id = current_user.id
    session.add(event)
    session.commit()
    session.refresh(event)
    
    # 简单同步逻辑：如果是完成事件，则更新用户的汇总进度
    # 复杂系统中可能会将此逻辑移到异步任务中处理
    if event.event_type == EventType.FINISH:
        progress = session.exec(select(UserProgress).where(UserProgress.user_id == current_user.id)).first()
        if not progress:
            # 如果没有进度记录则创建
            progress = UserProgress(user_id=current_user.id)
            session.add(progress)
        
        # 累加学习时间（将秒转换为分钟）
        progress.total_study_time_min += (event.duration_sec / 60.0)
        progress.updated_at = datetime.utcnow()
        session.add(progress)
        session.commit()
        
    return event

@router.get("/events", response_model=List[EventLog], summary="获取事件日志列表")
async def list_events(
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    获取当前用户的事件日志列表，支持分页，按创建时间倒序排列。

    Args:
        limit (int): 返回的最大事件数量，默认为 50。
        offset (int): 结果的偏移量，用于分页，默认为 0。
        current_user (User): 当前认证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[EventLog]: 事件日志列表。
    """
    # 构建查询语句并执行分页
    statement = select(EventLog).where(EventLog.user_id == current_user.id).order_by(EventLog.created_at.desc()).offset(offset).limit(limit)
    events = session.exec(statement).all()
    return events
