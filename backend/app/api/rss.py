from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Body, BackgroundTasks
from sqlmodel import Session, select, func
from sqlalchemy import or_
from sqlalchemy.orm import selectinload
from app.core.database import get_session
from app.core.dependencies import get_rss_group_service
from app.models.rss import (
    RSSFeed, RSSFeedCreate, RSSFeedRead, RSSFeedUpdate,
    RSSGroup, RSSGroupCreate, RSSGroupRead, RSSGroupUpdate,
    RSSArticle, RSSArticleRead, BatchDelete, RSSFeedGroupLink
)
from app.services import rss_service
from pydantic import BaseModel
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Feed Management ---

def _build_rss_group_read(group: RSSGroup, feeds_count: int = 0) -> RSSGroupRead:
    return RSSGroupRead(
        name=group.name,
        user_id=group.user_id,
        parent_id=group.parent_id,
        icon=group.icon,
        color=group.color,
        order=group.order,
        id=group.id,
        children=[],
        feeds_count=feeds_count
    )

def _build_rss_feed_read(feed: RSSFeed, articles_count: int = 0) -> RSSFeedRead:
    groups = [_build_rss_group_read(g) for g in feed.groups] if feed.groups else []
    return RSSFeedRead(
        url=feed.url,
        user_id=feed.user_id,
        title=feed.title,
        description=feed.description,
        group_name=feed.group_name,
        is_active=feed.is_active,
        is_whitelisted=feed.is_whitelisted,
        id=feed.id,
        last_fetched_at=feed.last_fetched_at,
        last_fetch_status=feed.last_fetch_status,
        error_message=feed.error_message,
        articles_count=articles_count,
        groups=groups
    )

@router.get("/feeds", response_model=List[RSSFeedRead], summary="获取所有订阅源")
def get_feeds(session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    获取所有的 RSS 订阅源，并返回包含分组信息和文章数量的详细数据。

    Args:
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[RSSFeedRead]: 包含订阅源详情的列表。
    """
    # 使用预加载 (eager loading) 避免 groups 的 N+1 查询问题
    statement = select(RSSFeed).options(selectinload(RSSFeed.groups))
    feeds = session.exec(statement).all()

    # 批量查询各订阅源的文章数量，避免在循环中产生 N+1 查询
    # 按照 feed_id 进行分组统计
    article_counts = session.exec(
        select(RSSArticle.feed_id, func.count(RSSArticle.id))
        .group_by(RSSArticle.feed_id)
    ).all()
    # 转换为字典格式，方便后续快速查找: {feed_id: count}
    count_map = {feed_id: count for feed_id, count in article_counts}

    # 丰富返回数据，加入分组信息和文章统计数量
    results = []
    for feed in feeds:
        try:
            articles_count = count_map.get(feed.id, 0)
            results.append(_build_rss_feed_read(feed, articles_count))
        except Exception as e:
            logger.error(f"Error processing feed {feed.id} for display: {e}")
            # 遇到处理异常时跳过当前记录，避免整个列表请求崩溃
            continue

    return results

@router.post("/feeds", response_model=RSSFeedRead, summary="添加订阅源")
def add_feed(feed_in: RSSFeedCreate, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    添加一个新的 RSS 订阅源。如果订阅源 URL 已经存在，则直接返回已存在的记录，
    否则将抓取并解析 RSS 内容，保存到数据库中。

    Args:
        feed_in (RSSFeedCreate): 创建订阅源的请求数据模型。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 当抓取或创建订阅源失败时抛出 400 或 500 异常。

    Returns:
        RSSFeedRead: 添加成功后的订阅源详细信息。
    """
    # 检查数据库中是否已存在相同的订阅源 URL
    existing_feed = session.exec(select(RSSFeed).where(RSSFeed.url == feed_in.url)).first()

    feed = None
    if existing_feed:
        feed = existing_feed
    else:
        # 如果不存在，尝试抓取并创建新的订阅源
        try:
            # 调用 service 层的逻辑抓取并解析内容
            rss_service.fetch_and_parse_feed(feed_in.url, session)
            # 重新查询数据库确认是否创建成功
            feed = session.exec(select(RSSFeed).where(RSSFeed.url == feed_in.url)).first()
            if not feed:
                 raise HTTPException(status_code=500, detail="Failed to create feed")
        except Exception as e:
            logger.error(f"Failed to add feed {feed_in.url}: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    # 如果请求中包含了分组信息，则设置该订阅源的分组关联
    if feed_in.group_ids is not None:
         rss_group_service.set_feed_groups(session, feed.id, feed_in.group_ids)
         # 刷新对象以获取最新的分组信息
         session.refresh(feed)

    # 构造返回的完整数据
    # 查询当前订阅源下文章的总数
    count = session.exec(select(func.count(RSSArticle.id)).where(RSSArticle.feed_id == feed.id)).one()
    return _build_rss_feed_read(feed, count)

@router.post("/feeds/{feed_id}/update", response_model=RSSFeedRead, summary="更新订阅源")
def update_feed(feed_id: int, feed_update: RSSFeedUpdate, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    更新指定 RSS 订阅源的基本信息和所属分组。

    Args:
        feed_id (int): 需要更新的订阅源 ID。
        feed_update (RSSFeedUpdate): 更新的数据模型。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果订阅源不存在，抛出 404 错误。

    Returns:
        RSSFeedRead: 更新后的订阅源详细信息。
    """
    feed = session.get(RSSFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    feed_data = feed_update.dict(exclude_unset=True)

    # 独立处理分组关联逻辑
    if "group_ids" in feed_data:
        group_ids = feed_data.pop("group_ids")
        if group_ids is not None:
            rss_group_service.set_feed_groups(session, feed.id, group_ids)

    # 更新其余的基本信息
    for key, value in feed_data.items():
        setattr(feed, key, value)

    session.add(feed)
    session.commit()
    session.refresh(feed)

    # 构建并返回包含关联数据的更新结果
    count = session.exec(select(func.count(RSSArticle.id)).where(RSSArticle.feed_id == feed.id)).one()
    return _build_rss_feed_read(feed, count)

@router.post("/feeds/{feed_id}/delete", summary="删除订阅源")
def delete_feed(feed_id: int, session: Session = Depends(get_session)):
    """
    删除指定的 RSS 订阅源及其关联信息。

    Args:
        feed_id (int): 要删除的订阅源 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果订阅源不存在，抛出 404 错误。

    Returns:
        dict: 操作成功的提示信息。
    """
    feed = session.get(RSSFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    # 首先清理订阅源和分组之间的关联关系
    links = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.feed_id == feed_id)).all()
    for link in links:
        session.delete(link)

    # 删除订阅源主体
    session.delete(feed)
    session.commit()
    return {"message": "Feed deleted successfully"}

@router.post("/feeds/batch_delete", summary="批量删除订阅源")
def batch_delete_feeds(batch: BatchDelete, session: Session = Depends(get_session)):
    """
    批量删除多个 RSS 订阅源及其关联的分组信息。

    Args:
        batch (BatchDelete): 包含要删除的订阅源 ID 列表的模型。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        dict: 操作成功的提示信息。
    """
    for feed_id in batch.feed_ids:
        feed = session.get(RSSFeed, feed_id)
        if feed:
            # 清理订阅源和分组之间的关联关系
            links = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.feed_id == feed_id)).all()
            for link in links:
                session.delete(link)
            # 删除订阅源主体
            session.delete(feed)

    # 批量提交更改
    session.commit()
    return {"message": "Feeds deleted successfully"}

@router.post("/feeds/{feed_id}/refresh", summary="刷新单个订阅源")
def refresh_feed(feed_id: int, session: Session = Depends(get_session)):
    """
    手动触发刷新指定的 RSS 订阅源，重新抓取最新的文章。

    Args:
        feed_id (int): 要刷新的订阅源 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果订阅源不存在抛出 404；抓取失败抛出 500。

    Returns:
        dict: 刷新成功的提示及新增文章的数量。
    """
    feed = session.get(RSSFeed, feed_id)
    if not feed:
        raise HTTPException(status_code=404, detail="Feed not found")

    try:
        # 调用服务层执行抓取操作，并获取新增的文章数量
        count = rss_service.fetch_and_parse_feed(feed.url, session, feed_id=feed.id)
        return {"message": "Feed refreshed successfully", "new_articles_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feeds/refresh", summary="刷新所有订阅源")
def refresh_feeds(background_tasks: BackgroundTasks):
    """
    将刷新所有订阅源的任务添加到后台执行队列中，避免阻塞当前请求。

    Args:
        background_tasks (BackgroundTasks): FastAPI 后台任务管理器。

    Returns:
        dict: 任务调度成功的提示信息。
    """
    from app.services.rss_service import update_all_feeds_background
    background_tasks.add_task(update_all_feeds_background)
    return {"message": "All feeds refresh scheduled"}

@router.post("/feeds/import", summary="导入 OPML")
def import_opml(content: str = Body(..., embed=True), session: Session = Depends(get_session)):
    """
    从提供的 OPML 内容中解析并导入多个 RSS 订阅源。

    Args:
        content (str): OPML 文件的内容字符串。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 当 OPML 内容无效或解析失败时抛出 400 错误。

    Returns:
        dict: 成功导入的订阅源数量提示信息。
    """
    import xml.etree.ElementTree as ET
    try:
        # 解析 XML 内容
        root = ET.fromstring(content)
        count = 0
        # 递归搜索具有 xmlUrl 属性的 outline 节点
        for outline in root.findall(".//outline[@xmlUrl]"):
            url = outline.get("xmlUrl")
            if url:
                try:
                    # 尝试抓取并解析找到的订阅源
                    rss_service.fetch_and_parse_feed(url, session)
                    count += 1
                except Exception as e:
                    # 单个订阅源导入失败仅记录日志，不影响整体流程
                    logger.error(f"Failed to import {url}: {e}")
                    pass
        return {"message": f"Imported {count} feeds"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid OPML: {str(e)}")

@router.post("/feeds/cleanup_failed", summary="清理抓取失败的订阅源")
def cleanup_failed_feeds(session: Session = Depends(get_session)):
    """
    清理数据库中最后一次抓取状态为 "error" 的所有 RSS 订阅源。

    Args:
        session (Session): 数据库会话（依赖注入）。

    Returns:
        dict: 清理成功的提示及清理的订阅源数量。
    """
    # 查询所有处于错误状态的订阅源
    feeds = session.exec(select(RSSFeed).where(RSSFeed.last_fetch_status == "error")).all()
    count = len(feeds)
    for feed in feeds:
        # 清理关联的分组信息
        links = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.feed_id == feed.id)).all()
        for link in links:
            session.delete(link)
        # 删除订阅源
        session.delete(feed)
    session.commit()
    return {"message": f"Cleaned up {count} failed feeds"}



# --- Group Management ---

@router.post("/groups", response_model=RSSGroupRead, summary="创建分组")
def create_group(group: RSSGroupCreate, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    创建一个新的 RSS 订阅源分组。

    Args:
        group (RSSGroupCreate): 创建分组的数据模型。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        RSSGroupRead: 创建成功的分组详情。
    """
    new_group = rss_group_service.create_group(session, group)
    return RSSGroupRead(
        name=new_group.name,
        user_id=new_group.user_id,
        parent_id=new_group.parent_id,
        icon=new_group.icon,
        color=new_group.color,
        order=new_group.order,
        id=new_group.id,
        children=[],
        feeds_count=0
    )

@router.get("/groups", response_model=List[RSSGroupRead], summary="获取所有分组")
def get_groups(parent_id: Optional[int] = None, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    获取分组列表。如果指定了 parent_id，则返回该父分组下的子分组。

    Args:
        parent_id (Optional[int], optional): 父分组的 ID。默认为 None 返回顶层或所有。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[RSSGroupRead]: 分组详情的列表。
    """
    groups = rss_group_service.get_groups(session, parent_id)
    # 构建响应
    results = []
    for group in groups:
        # Pydantic v2 兼容: 将 SQLAlchemy 关系属性提前转换以避免 list 验证错误
        group_dict = {
            "name": group.name,
            "user_id": group.user_id,
            "parent_id": group.parent_id,
            "icon": group.icon,
            "color": group.color,
            "order": group.order,
            "id": group.id,
            "children": [],
            "feeds_count": len(group.feeds) if group.feeds else 0
        }
        results.append(RSSGroupRead(**group_dict))

    return results

@router.get("/groups/tree", response_model=List[Dict[str, Any]], summary="获取分组树形结构")
def get_groups_tree(session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    获取包含层级关系的所有分组树形结构。

    Args:
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[Dict[str, Any]]: 树形结构的分组列表。
    """
    return rss_group_service.get_groups_tree(session)

@router.get("/articles", response_model=List[RSSArticleRead], summary="获取文章列表")
def get_articles(
    feed_id: Optional[int] = Query(None, description="订阅源ID"),
    group_id: Optional[int] = Query(None, description="分组ID"),
    limit: int = Query(20, description="限制返回数量"),
    offset: int = Query(0, description="偏移量"),
    q: Optional[str] = Query(None, description="关键词搜索（标题、摘要、内容）"),
    session: Session = Depends(get_session)
):
    """
    分页获取 RSS 文章列表，支持按订阅源或分组进行筛选。

    Args:
        feed_id (Optional[int], optional): 指定的订阅源 ID。
        group_id (Optional[int], optional): 指定的分组 ID。
        limit (int, optional): 返回文章的数量限制。默认 20。
        offset (int, optional): 分页偏移量。默认 0。
        q (Optional[str], optional): 关键词搜索（匹配标题、摘要、内容）。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[RSSArticleRead]: 包含文章详情及对应订阅源标题的列表。
    """
    # 预加载对应的 feed 信息以避免后续的 N+1 查询
    statement = select(RSSArticle).options(selectinload(RSSArticle.feed))

    if feed_id is not None:
        statement = statement.where(RSSArticle.feed_id == feed_id)
    elif group_id is not None:
        # 查找属于该分组的所有 feed
        feed_links = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.group_id == group_id)).all()
        feed_ids = [link.feed_id for link in feed_links]
        if feed_ids:
            statement = statement.where(RSSArticle.feed_id.in_(feed_ids))
        else:
            # 该分组下没有关联的 feed，直接返回空列表
            return []

    if q:
        statement = statement.where(
            or_(
                RSSArticle.title.contains(q),
                RSSArticle.summary.contains(q),
                RSSArticle.content.contains(q),
            )
        )

    # 按发布时间倒序排列，并应用分页参数
    statement = statement.order_by(RSSArticle.published_at.desc()).offset(offset).limit(limit)
    articles = session.exec(statement).all()

    # 丰富数据：将 feed 的标题添加到返回对象中
    results = []
    for article in articles:
        article_read = RSSArticleRead.from_orm(article)
        if article.feed:
            article_read.feed_title = article.feed.title
        results.append(article_read)

    return results

@router.get("/articles/{article_id}", response_model=RSSArticleRead, summary="获取单篇文章详情")
def get_article(article_id: int, session: Session = Depends(get_session)):
    """
    获取指定 ID 的文章详情。

    Args:
        article_id (int): 文章的唯一 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果文章不存在，抛出 404 错误。

    Returns:
        RSSArticleRead: 包含关联订阅源标题的文章详情。
    """
    statement = select(RSSArticle).options(selectinload(RSSArticle.feed)).where(RSSArticle.id == article_id)
    article = session.exec(statement).first()
    if not article:
        raise HTTPException(status_code=404, detail="Article not found")

    article_read = RSSArticleRead.from_orm(article)
    if article.feed:
        article_read.feed_title = article.feed.title
    return article_read

@router.post("/groups/{group_id}/update", response_model=RSSGroupRead, summary="更新分组")
def update_group(group_id: int, group_update: RSSGroupUpdate, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    更新指定分组的名称或层级信息。

    Args:
        group_id (int): 要更新的分组 ID。
        group_update (RSSGroupUpdate): 包含更新内容的数据模型。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果分组不存在，抛出 404 错误。

    Returns:
        RSSGroupRead: 更新成功的分组详情。
    """
    group = rss_group_service.update_group(session, group_id, group_update)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")
    return RSSGroupRead(
        name=group.name,
        user_id=group.user_id,
        parent_id=group.parent_id,
        icon=group.icon,
        color=group.color,
        order=group.order,
        id=group.id,
        children=[],
        feeds_count=len(group.feeds) if group.feeds else 0
    )

@router.post("/groups/{group_id}/delete", summary="删除分组")
def delete_group(group_id: int, session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    删除指定的分组。

    Args:
        group_id (int): 要删除的分组 ID。
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 如果分组不存在或删除失败，抛出 404 错误。

    Returns:
        dict: 删除成功的提示信息。
    """
    success = rss_group_service.delete_group(session, group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Group not found")
    return {"message": "Group deleted successfully"}

@router.post("/feeds/{feed_id}/groups", summary="设置订阅源分组")
def set_feed_groups(feed_id: int, group_ids: List[int], session: Session = Depends(get_session), rss_group_service=Depends(get_rss_group_service)):
    """
    为指定的 RSS 订阅源分配一个或多个分组。

    Args:
        feed_id (int): 订阅源 ID。
        group_ids (List[int]): 目标分组 ID 列表。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        dict: 设置成功的提示信息。
    """
    rss_group_service.set_feed_groups(session, feed_id, group_ids)
    return {"message": "Feed groups updated successfully"}

# --- Cleanup ---

class CleanupQuery(BaseModel):
    threshold: int = 3

@router.post("/cleanup/candidates", response_model=List[RSSFeedRead], summary="获取待清理订阅源列表")
def get_cleanup_candidates(query: CleanupQuery, session: Session = Depends(get_session)):
    """
    获取文章数量少于指定阈值的待清理订阅源列表。

    Args:
        query (CleanupQuery): 包含清理阈值的查询参数。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        List[RSSFeedRead]: 待清理的订阅源列表。
    """
    # 联表查询订阅源及其文章，并按照文章数量进行过滤
    stmt = select(RSSFeed, func.count(RSSArticle.id)).join(RSSArticle, isouter=True).group_by(RSSFeed.id).having(func.count(RSSArticle.id) < query.threshold)
    results = session.exec(stmt).all()

    feeds = []
    for feed, count in results:
        feeds.append(_build_rss_feed_read(feed, count))
    return feeds

@router.post("/cleanup/execute", summary="执行清理")
def execute_cleanup(batch: BatchDelete, session: Session = Depends(get_session)):
    """
    执行批量删除订阅源的清理操作。

    Args:
        batch (BatchDelete): 要清理的订阅源 ID 列表。
        session (Session): 数据库会话（依赖注入）。

    Returns:
        dict: 清理执行成功的提示信息。
    """
    # 复用批量删除的逻辑
    return batch_delete_feeds(batch, session)

@router.post("/feeds/auto_classify", summary="智能分类订阅源")
def auto_classify(session: Session = Depends(get_session)):
    """
    触发对所有的订阅源进行智能分类并自动分组。

    Args:
        session (Session): 数据库会话（依赖注入）。

    Raises:
        HTTPException: 当智能分类执行失败时抛出 500 错误。

    Returns:
        dict: 自动分类任务的执行结果。
    """
    try:
        return rss_service.auto_classify_feeds(session)
    except Exception as e:
        logger.error(f"Auto classify failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
