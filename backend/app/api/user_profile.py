from fastapi import APIRouter, Depends
from sqlmodel import Session
from typing import List
from app.core.database import get_session
from app.core.dependencies import get_user_profile_service
from app.models.user_profile import UserProfile, UserProfileUpdate, UserProfileHistory

router = APIRouter()


@router.get("/", response_model=UserProfile, summary="获取用户个人信息")
async def get_user_profile(
    session: Session = Depends(get_session),
    svc=Depends(get_user_profile_service),
):
    return svc.get_profile(session)


@router.post("/", response_model=UserProfile, summary="更新用户个人信息")
async def update_user_profile(
    update_data: UserProfileUpdate,
    session: Session = Depends(get_session),
    svc=Depends(get_user_profile_service),
):
    return svc.update_profile(session, update_data)


@router.get("/history", response_model=List[UserProfileHistory], summary="获取用户个人信息修改历史")
async def get_user_profile_history(
    limit: int = 10,
    session: Session = Depends(get_session),
    svc=Depends(get_user_profile_service),
):
    return svc.get_history(session, limit)
