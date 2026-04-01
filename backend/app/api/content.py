from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.auth import get_current_active_user, User
from app.models.content import ContentRepo, ContentRepoCreate, ContentRepoRead

# 创建内容相关的 API 路由
router = APIRouter()

@router.post("/", response_model=ContentRepoRead, summary="创建内容记录")
async def create_content(
    content_data: ContentRepoCreate,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    创建一条新的内容记录。

    Args:
        content_data (ContentRepoCreate): 要创建的内容数据，包括关联的任务 ID、内容类型和具体内容。
        current_user (User): 当前经过身份验证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        ContentRepoRead: 创建成功的内容记录详情。
    """
    # TODO: 未来需要添加权限检查逻辑，验证当前用户是否拥有该内容关联的任务（task -> milestone -> plan -> user_id）。
    # 目前假设只有经过授权的 Agent 或用户可以创建内容。
    
    # 从 Pydantic 模型创建 ORM 实例
    content = ContentRepo.from_orm(content_data)
    
    # 添加到会话并提交到数据库
    session.add(content)
    session.commit()
    # 刷新实例以获取数据库生成的字段（如 ID、创建时间等）
    session.refresh(content)
    
    return content

@router.get("/task/{task_id}", response_model=List[ContentRepoRead], summary="获取任务的内容列表")
async def list_content_by_task(
    task_id: int,
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_session)
):
    """
    根据任务 ID 获取该任务关联的所有内容记录。

    Args:
        task_id (int): 目标任务的 ID。
        current_user (User): 当前经过身份验证的用户（依赖注入）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[ContentRepoRead]: 与该任务关联的内容记录列表。
    """
    # 理想情况下，这里也需要进行权限检查，确保用户有权访问该任务的内容。
    
    # 构建查询语句，筛选 task_id 匹配的内容记录
    statement = select(ContentRepo).where(ContentRepo.task_id == task_id)
    # 执行查询并获取所有结果
    contents = session.exec(statement).all()
    
    return contents

