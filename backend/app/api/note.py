from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import Session, select
from app.core.database import get_session
from app.models.note import (
    ArticleNote, ArticleNoteCreate, ArticleNoteRead, ArticleNoteUpdate,
    ArticleSummary, ArticleSummaryCreate, ArticleSummaryRead, ArticleSummaryUpdate
)

# 创建笔记与摘要相关的 API 路由
router = APIRouter()

# --- Notes (笔记相关接口) ---

@router.post("", response_model=ArticleNoteRead, summary="Create a new note")
def create_note(note: ArticleNoteCreate, session: Session = Depends(get_session)):
    """
    创建一条新的文章笔记。

    Args:
        note (ArticleNoteCreate): 创建笔记的请求数据，包含文章 ID、笔记内容及相关的上下文信息。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        ArticleNoteRead: 创建成功的笔记记录。
    """
    db_note = ArticleNote.model_validate(note)
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note

@router.get("/article/{article_id}", response_model=List[ArticleNoteRead], summary="Get all notes for an article")
def get_notes_by_article(article_id: int, session: Session = Depends(get_session)):
    """
    获取指定文章的所有笔记记录，并按在文章中的起始位置排序。

    Args:
        article_id (int): 目标文章的 ID。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[ArticleNoteRead]: 该文章的笔记列表。
    """
    statement = select(ArticleNote).where(ArticleNote.article_id == article_id).order_by(ArticleNote.start_offset)
    results = session.exec(statement).all()
    return results

def _update_note_logic(db_note: ArticleNote, note_update: ArticleNoteUpdate, session: Session):
    """
    更新笔记的内部通用逻辑，用于处理 PUT 和 POST 更新请求。

    Args:
        db_note (ArticleNote): 数据库中已存在的笔记对象。
        note_update (ArticleNoteUpdate): 包含要更新的字段的数据。
        session (Session): 数据库会话。

    Returns:
        ArticleNote: 更新后的笔记对象。
    """
    note_data = note_update.dict(exclude_unset=True)
    for key, value in note_data.items():
        setattr(db_note, key, value)

    # 更新最后修改时间
    db_note.updated_at = datetime.now()
    session.add(db_note)
    session.commit()
    session.refresh(db_note)
    return db_note

@router.put("/{note_id}", response_model=ArticleNoteRead, summary="Update a note")
def update_note(note_id: int, note_update: ArticleNoteUpdate, session: Session = Depends(get_session)):
    """
    更新指定的笔记记录（PUT 方法）。

    Args:
        note_id (int): 要更新的笔记 ID。
        note_update (ArticleNoteUpdate): 要更新的字段内容。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到指定的笔记，抛出 404 错误。

    Returns:
        ArticleNoteRead: 更新后的笔记记录。
    """
    db_note = session.get(ArticleNote, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _update_note_logic(db_note, note_update, session)

@router.post("/{note_id}/update", response_model=ArticleNoteRead, summary="Update a note (POST)")
def update_note_post(note_id: int, note_update: ArticleNoteUpdate, session: Session = Depends(get_session)):
    """
    更新指定的笔记记录（POST 方法，用于兼容不支持 PUT 的客户端）。

    Args:
        note_id (int): 要更新的笔记 ID。
        note_update (ArticleNoteUpdate): 要更新的字段内容。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到指定的笔记，抛出 404 错误。

    Returns:
        ArticleNoteRead: 更新后的笔记记录。
    """
    db_note = session.get(ArticleNote, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    return _update_note_logic(db_note, note_update, session)

@router.delete("/{note_id}", summary="Delete a note")
def delete_note(note_id: int, session: Session = Depends(get_session)):
    """
    删除指定的笔记（DELETE 方法）。

    Args:
        note_id (int): 要删除的笔记 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到指定的笔记，抛出 404 错误。

    Returns:
        dict: 包含操作结果状态的字典。
    """
    db_note = session.get(ArticleNote, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    session.delete(db_note)
    session.commit()
    return {"ok": True}

@router.post("/{note_id}/delete", summary="Delete a note (POST)")
def delete_note_post(note_id: int, session: Session = Depends(get_session)):
    """
    删除指定的笔记（POST 方法，用于兼容不支持 DELETE 的客户端）。

    Args:
        note_id (int): 要删除的笔记 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到指定的笔记，抛出 404 错误。

    Returns:
        dict: 包含操作结果状态的字典。
    """
    db_note = session.get(ArticleNote, note_id)
    if not db_note:
        raise HTTPException(status_code=404, detail="Note not found")
    session.delete(db_note)
    session.commit()
    return {"ok": True}

@router.get("/summaries/article/{article_id}", response_model=Optional[ArticleSummaryRead], summary="Get summary for an article")
def get_summary_by_article(article_id: int, session: Session = Depends(get_session)):
    """
    获取指定文章的摘要。

    Args:
        article_id (int): 目标文章的 ID。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        Optional[ArticleSummaryRead]: 该文章的摘要，如果没有则返回 None。
    """
    statement = select(ArticleSummary).where(ArticleSummary.article_id == article_id)
    result = session.exec(statement).first()
    return result

@router.post("/summaries", response_model=ArticleSummaryRead, summary="Create or update summary")
def create_or_update_summary(
    summary: ArticleSummaryCreate,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session)
):
    """
    创建或更新文章的摘要记录。如果文章已有摘要则更新之，否则创建新的摘要。
    如果摘要不是草稿状态，将在后台任务中触发摘要内容的向量化处理。

    Args:
        summary (ArticleSummaryCreate): 摘要数据，包括文章 ID、内容、是否为草稿等。
        background_tasks (BackgroundTasks): FastAPI 后台任务对象，用于异步执行向量化。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        ArticleSummaryRead: 创建或更新后的摘要记录。
    """
    # 检查文章是否已存在摘要
    statement = select(ArticleSummary).where(ArticleSummary.article_id == summary.article_id)
    existing_summary = session.exec(statement).first()

    if existing_summary:
        # 存在则执行更新逻辑
        existing_summary.content = summary.content
        existing_summary.is_draft = summary.is_draft
        existing_summary.version += 1
        existing_summary.updated_at = datetime.now()
        existing_summary.is_vectorized = False # 内容变更，使现有向量数据失效
        session.add(existing_summary)
        session.commit()
        session.refresh(existing_summary)
        db_summary = existing_summary
    else:
        # 不存在则执行创建逻辑
        db_summary = ArticleSummary.model_validate(summary)
        session.add(db_summary)
        session.commit()
        session.refresh(db_summary)

    # 如果摘要不是草稿状态，理论上应触发向量化任务，由于 vector_store 已迁移，这里留空或调用远程服务
    # if not db_summary.is_draft:
    #      background_tasks.add_task(remote_vector_service.vectorize_summary, db_summary.id)

    return db_summary

@router.post("/summaries/{summary_id}/delete", summary="Delete a summary (POST)")
def delete_summary_post(summary_id: int, session: Session = Depends(get_session)):
    """
    删除指定的文章摘要（POST 方法，用于兼容不支持 DELETE 的客户端）。
    如果该摘要已被向量化，同时从向量存储中删除对应数据。

    Args:
        summary_id (int): 要删除的摘要 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果找不到指定的摘要，抛出 404 错误。

    Returns:
        dict: 包含操作结果状态的字典。
    """
    db_summary = session.get(ArticleSummary, summary_id)
    if not db_summary:
        raise HTTPException(status_code=404, detail="Summary not found")

    # 如果摘要已向量化，理论上应尝试从向量数据库中删除
    # 由于 vector_store 已迁移，此处不再执行本地向量删除操作
    # if db_summary.is_vectorized:
    #     try:
    #         remote_vector_service.delete(where={"summary_id": summary_id})
    #     except Exception as e:
    #         print(f"Failed to delete vector for summary {summary_id}: {e}")

    session.delete(db_summary)
    session.commit()
    return {"ok": True}

@router.delete("/summaries/{summary_id}", summary="Delete a summary")
def delete_summary(summary_id: int, session: Session = Depends(get_session)):
    """
    删除指定的文章摘要（DELETE 方法）。

    Args:
        summary_id (int): 要删除的摘要 ID。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        dict: 包含操作结果状态的字典。
    """
    return delete_summary_post(summary_id, session)

@router.get("/summaries/article/{article_id}", response_model=Optional[ArticleSummaryRead], summary="Get summary for an article")
def get_summary_by_article(article_id: int, session: Session = Depends(get_session)):
    """
    获取指定文章的摘要记录。

    Args:
        article_id (int): 目标文章的 ID。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        Optional[ArticleSummaryRead]: 该文章的摘要记录，如果不存在则返回 None。
    """
    statement = select(ArticleSummary).where(ArticleSummary.article_id == article_id)
    result = session.exec(statement).first()
    # 如果未找到，返回 None (常见做法是 200 OK 带 null 体)
    if not result:
        return None
    return result
