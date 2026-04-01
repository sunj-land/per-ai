from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.auth import get_current_active_user, User
from app.models.reminder import (
    UserReminder, UserReminderCreate, UserReminderRead, ReminderMethod
)

router = APIRouter()

@router.get("/", response_model=List[UserReminderRead], summary="获取当前用户的所有提醒")
async def list_reminders(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    获取当前登录用户的所有提醒列表。

    Args:
        current_user (User): 当前认证的用户对象（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[UserReminderRead]: 包含当前用户所有提醒信息的列表。
    """
    # 构造查询，根据当前用户 ID 筛选提醒
    statement = select(UserReminder).where(UserReminder.user_id == current_user.id)
    # 执行查询并获取所有匹配的记录
    reminders = session.exec(statement).all()
    return reminders

@router.post("/", response_model=UserReminderRead, summary="创建新的提醒")
async def create_reminder(
    reminder_data: UserReminderCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    为当前登录用户创建一个新的提醒。

    Args:
        reminder_data (UserReminderCreate): 创建提醒所需的数据模型。
        current_user (User): 当前认证的用户对象（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        UserReminderRead: 创建成功后的提醒信息。
    """
    # 将请求数据模型转换为数据库模型
    reminder = UserReminder.from_orm(reminder_data)
    # 绑定当前用户的 ID
    reminder.user_id = current_user.id

    # 添加到数据库会话并提交
    session.add(reminder)
    session.commit()
    # 刷新以获取数据库生成的 ID 和其他默认字段
    session.refresh(reminder)

    return reminder

@router.delete("/{reminder_id}", summary="删除指定的提醒")
async def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    删除指定的提醒。只能删除属于当前用户的提醒。

    Args:
        reminder_id (int): 要删除的提醒的唯一 ID。
        current_user (User): 当前认证的用户对象（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果提醒不存在，或者不属于当前用户，抛出 404 错误。

    Returns:
        dict: 包含状态信息的字典，表示删除成功。
    """
    # 根据 ID 查找提醒
    reminder = session.get(UserReminder, reminder_id)

    # 验证提醒是否存在以及是否属于当前用户
    if not reminder or reminder.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Reminder not found")

    # 从数据库中删除并提交
    session.delete(reminder)
    session.commit()

    return {"status": "ok"}
