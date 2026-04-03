from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List, Optional
from app.core.database import get_session
from app.core.dependencies import get_user_profile_service
from app.core.auth import get_current_active_user
from app.models.user import User
from app.models.user_profile import UserProfile, UserProfileUpdate, UserProfileHistory

router = APIRouter()


@router.get("/", response_model=UserProfile, summary="获取当前用户个人信息")
async def get_user_profile(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    svc=Depends(get_user_profile_service),
):
    """
    获取当前登录用户的个人信息配置。
    
    业务逻辑：
    - 从 JWT token 中获取当前用户信息
    - 查询该用户的个人信息配置
    - 如果不存在，自动创建默认配置
    
    Returns:
        UserProfile: 当前用户的个人信息对象
    """
    return svc.get_profile(session, current_user.id)


@router.post("/", response_model=UserProfile, summary="更新当前用户个人信息")
async def update_user_profile(
    update_data: UserProfileUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    svc=Depends(get_user_profile_service),
):
    """
    更新当前登录用户的个人信息。
    
    业务逻辑：
    - 从 JWT token 中获取当前用户信息
    - 保存当前配置到历史记录表（版本管理）
    - 更新用户的个人信息配置
    
    Args:
        update_data: 包含要更新的 identity 和/或 rules 数据
        
    Returns:
        UserProfile: 更新后的用户个人信息对象
    """
    return svc.update_profile(session, current_user.id, update_data)


@router.get("/history", response_model=List[UserProfileHistory], summary="获取用户个人信息修改历史")
async def get_user_profile_history(
    limit: int = 10,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    svc=Depends(get_user_profile_service),
):
    """
    获取当前用户的个人信息修改历史记录。
    
    业务逻辑：
    - 从 JWT token 中获取当前用户信息
    - 查询该用户的配置变更历史
    - 按版本号倒序返回
    
    Args:
        limit: 返回记录的最大数量，默认 10 条
        
    Returns:
        List[UserProfileHistory]: 历史记录列表
    """
    return svc.get_history(session, current_user.id, limit)


@router.post("/rollback/{version}", response_model=UserProfile, summary="回溯到指定版本")
async def rollback_to_version(
    version: int,
    change_reason: Optional[str] = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_active_user),
    svc=Depends(get_user_profile_service),
):
    """
    将当前用户的配置回溯到指定版本。
    
    业务逻辑：
    - 从 JWT token 中获取当前用户信息
    - 查询目标版本的历史记录
    - 保存当前配置作为备份版本
    - 应用历史版本的配置
    
    Args:
        version: 目标版本号
        change_reason: 变更原因说明，可选
        
    Returns:
        UserProfile: 回溯后的用户个人信息对象
        
    Raises:
        HTTPException: 目标版本不存在时返回 404 错误
    """
    try:
        return svc.rollback_to_version(
            session, 
            current_user.id, 
            version, 
            change_reason
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
