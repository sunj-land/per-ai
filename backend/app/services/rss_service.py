import feedparser
import hashlib
import httpx
from datetime import datetime
from sqlmodel import Session, select
from app.models.rss import RSSFeed, RSSArticle, RSSGroup, RSSFeedGroupLink
from app.core.database import engine
from app.core.html_utils import clean_html_content
from app.services.chat_service import ChatService
from sqlmodel import Session, select, col
from sqlalchemy.orm import selectinload
import logging
import json

logger = logging.getLogger(__name__)

def get_content_hash(content: str) -> str:
    """
    计算内容的 MD5 哈希值，用于文章去重。

    Args:
        content (str): 需要计算哈希的字符串内容。

    Returns:
        str: 32位十六进制的 MD5 哈希字符串。
    """
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def parse_published_at(entry) -> datetime:
    """
    解析 RSS 条目中的发布时间。
    尝试从 'published_parsed' 或 'updated_parsed' 字段获取时间。
    如果解析失败，则返回当前时间。

    Args:
        entry: feedparser 解析后的条目对象。

    Returns:
        datetime: 解析出的发布时间或当前时间。
    """
    if hasattr(entry, 'published_parsed') and entry.published_parsed:
        return datetime(*entry.published_parsed[:6])
    if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6])
    return datetime.now()

def fetch_feed_content(url: str) -> str:
    """
    同步获取 RSS 源的 XML 内容。

    Args:
        url (str): RSS 源的 URL 地址。

    Returns:
        str: 获取到的 XML 文本内容。

    Raises:
        httpx.HTTPStatusError: 如果请求返回非 2xx 状态码。
    """
    with httpx.Client(follow_redirects=True, timeout=30.0) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = client.get(url, headers=headers)
        response.raise_for_status()
        return response.text

def fetch_and_parse_feed(feed_url: str, session: Session, feed_id: int = None):
    """
    核心业务逻辑：抓取并解析 RSS 源，更新数据库中的订阅源和文章信息。

    业务流程：
    1. 根据 feed_id 或 feed_url 查询现有的订阅源，如果禁用则跳过。
    2. 下载 RSS XML 内容，使用 feedparser 解析。
    3. 更新或创建 RSSFeed 记录（标题、描述、状态等）。
    4. 遍历解析出的文章列表，清理 HTML 标签，基于 content_hash 或链接进行去重。
    5. 保存新文章到数据库。

    Args:
        feed_url (str): RSS 源 URL。
        session (Session): 数据库会话。
        feed_id (int, optional): 如果已知 Feed ID，则直接更新该 Feed；否则根据 URL 查找或创建。

    Returns:
        int: 本次新增的文章数量。
    """
    # 尝试获取 Feed 对象
    feed = None
    if feed_id:
        feed = session.get(RSSFeed, feed_id)
    else:
        statement = select(RSSFeed).where(RSSFeed.url == feed_url)
        feed = session.exec(statement).first()

    # 如果 Feed 存在且被禁用，则跳过
    if feed and not feed.is_active:
        logger.info(f"Feed {feed_url} is disabled, skipping.")
        return 0

    try:
        content = fetch_feed_content(feed_url)
        parsed = feedparser.parse(content)

        if not getattr(parsed, 'version', None):
            raise ValueError("提供的 URL 不是有效的 RSS/Atom 订阅源格式")

        if parsed.bozo:
            logger.warning(f"Error parsing feed {feed_url}: {parsed.bozo_exception}")
            # 继续执行，因为 feedparser 通常可以部分解析出内容

        feed_title = parsed.feed.get('title', feed_url)
        feed_desc = parsed.feed.get('description', '')

        # 更新或创建 Feed
        if feed:
            feed.title = feed_title
            feed.description = feed_desc
            feed.last_fetched_at = datetime.now()
            feed.last_fetch_status = 'success'
            feed.error_message = None
            session.add(feed)
            session.commit()
            session.refresh(feed)
        else:
            feed = RSSFeed(
                url=feed_url,
                title=feed_title,
                description=feed_desc,
                last_fetched_at=datetime.now(),
                last_fetch_status='success',
                error_message=None
            )
            session.add(feed)
            session.commit()
            session.refresh(feed)

        new_articles_count = 0
        for entry in parsed.entries:
            link = entry.get('link', '')
            title = entry.get('title', 'No Title')
            summary = entry.get('summary', '')
            content = ''
            if hasattr(entry, 'content') and entry.content:
                content = entry.content[0].value
            elif hasattr(entry, 'description'):
                content = entry.description

            # 清理 HTML 内容
            content = clean_html_content(content)
            summary = clean_html_content(summary)

            # 使用链接或者标题+摘要作为唯一性判断依据
            unique_str = link if link else (title + summary)
            content_hash = get_content_hash(unique_str)

            # 提取分类信息
            category = None
            if hasattr(entry, 'tags') and entry.tags:
                category = entry.tags[0].term

            # 提取附件/媒体信息
            enclosure_url = None
            enclosure_type = None
            if hasattr(entry, 'enclosures') and entry.enclosures:
                enclosure_url = entry.enclosures[0].href
                enclosure_type = entry.enclosures[0].type

            # 通过链接或哈希检查文章是否已存在
            statement = select(RSSArticle).where((RSSArticle.link == link) | (RSSArticle.content_hash == content_hash))
            existing_article = session.exec(statement).first()

            if not existing_article:
                published_at = parse_published_at(entry)
                article = RSSArticle(
                    feed_id=feed.id,
                    title=title,
                    link=link,
                    summary=summary,
                    content=content,
                    published_at=published_at,
                    author=entry.get('author', ''),
                    content_hash=content_hash,
                    category=category,
                    enclosure_url=enclosure_url,
                    enclosure_type=enclosure_type
                )
                session.add(article)
                new_articles_count += 1

        session.commit()
        return new_articles_count

    except Exception as e:
        session.rollback()
        import traceback
        traceback.print_exc()
        logger.error(f"Failed to fetch feed {feed_url}: {e!r}")

        # 如果出错，更新 Feed 状态为 error
        if feed:
            feed.last_fetch_status = 'error'
            feed.error_message = str(e)
            session.add(feed)
            session.commit()
            session.refresh(feed)
        return 0

def update_all_feeds_background():
    """
    后台任务：刷新所有订阅源
    """
    with Session(engine) as session:
        feeds = session.exec(select(RSSFeed).where(RSSFeed.is_active == True)).all()
        logger.info(f"Starting background refresh for {len(feeds)} feeds...")
        count = 0
        for feed in feeds:
            try:
                fetch_and_parse_feed(feed.url, session, feed_id=feed.id)
                count += 1
            except Exception as e:
                logger.error(f"Failed to refresh feed {feed.url}: {e}")
        logger.info(f"Background refresh completed. Updated {count} feeds.")

def auto_classify_feeds(session: Session) -> dict:
    """
    自动对未分类的订阅源进行智能分类。

    处理流程：
    1. 迁移旧版 group_name 数据到新的分组关联表。
    2. 获取所有启用的且尚未分配分组的订阅源。
    3. 调用启用的 AI 模型，根据订阅源的标题和描述推荐合适的中文分类。
    4. 解析 AI 返回的 JSON 结果，自动创建分组并建立关联。

    Args:
        session (Session): 数据库会话。

    Returns:
        dict: 包含分类处理结果和统计数量的字典。
    """
    # 1. 迁移旧版数据
    migrated_count = migrate_legacy_groups(session)

    # 2. 获取未分类的订阅源 (没有关联分组的)
    all_feeds = session.exec(select(RSSFeed).where(RSSFeed.is_active == True)).all()
    unclassified_feeds = [f for f in all_feeds if not f.groups]

    if not unclassified_feeds:
        return {"count": migrated_count, "message": "No unclassified feeds found (excluding migrated)"}

    # 初始化 ChatService 获取 AI 模型
    chat_service = ChatService()
    enabled_models = chat_service.get_enabled_models()

    if not enabled_models:
        # 如果没有配置模型，直接返回
        return {"count": migrated_count, "message": "No AI models enabled for classification"}

    model_config = enabled_models[0] # 使用第一个可用模型
    provider, config = chat_service.get_provider_for_model(model_config["id"])

    if not provider:
         return {"count": migrated_count, "message": "Failed to initialize AI provider"}

    # 分批处理，避免单次 Prompt 过长导致 token 超限或处理失败
    BATCH_SIZE = 10
    processed_count = 0

    for i in range(0, len(unclassified_feeds), BATCH_SIZE):
        batch = unclassified_feeds[i:i+BATCH_SIZE]

        # 构建 Prompt 输入内容
        feeds_info = "\n".join([f"ID: {f.id}, Title: {f.title}, Desc: {f.description or ''}" for f in batch])

        prompt = f"""
        请对以下 RSS 订阅源进行分类。
        请根据标题和描述，为每个订阅源推荐一个最合适的中文分类名称（如：技术、新闻、娱乐、设计、生活、其他）。

        订阅源列表：
        {feeds_info}

        请严格按照 JSON 格式返回结果，格式如下：
        [
            {{"id": 订阅源ID, "category": "分类名称"}},
            ...
        ]
        只返回 JSON 数据，不要包含 markdown 代码块或其他文本。
        """

        try:
            # 调用 AI 接口进行推断
            messages = [{"role": "user", "content": prompt}]
            stream = provider.generate_stream(messages, config)

            response_text = ""
            for chunk in stream:
                response_text += chunk

            # 清理和解析 JSON 数据
            import json
            import re

            # 尝试提取文本中的 JSON 数组部分
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                json_str = response_text

            results = json.loads(json_str)

            # 应用 AI 返回的分类结果
            for item in results:
                feed_id = item.get("id")
                category = item.get("category")

                if feed_id and category:
                    # 查找是否已存在同名分组，不存在则创建
                    group = session.exec(select(RSSGroup).where(RSSGroup.name == category)).first()
                    if not group:
                        group = RSSGroup(name=category)
                        session.add(group)
                        session.commit()
                        session.refresh(group)

                    # 关联分组：检查是否已存在关联，不存在则创建
                    link = session.exec(select(RSSFeedGroupLink).where(
                        RSSFeedGroupLink.feed_id == feed_id,
                        RSSFeedGroupLink.group_id == group.id
                    )).first()

                    if not link:
                        link = RSSFeedGroupLink(feed_id=feed_id, group_id=group.id)
                        session.add(link)
                        processed_count += 1

            session.commit()

        except Exception as e:
            logger.error(f"Error classifying batch: {e}")
            continue

    total = migrated_count + processed_count
    return {"count": total, "message": f"Classified {processed_count} feeds, Migrated {migrated_count} feeds"}

def migrate_legacy_groups(session: Session) -> int:
    """
    将旧版订阅源表中的 group_name 字段数据迁移到新的分组关联表。

    处理流程：
    1. 查找所有 group_name 字段非空的 RSSFeed 记录。
    2. 根据 group_name 查找或创建 RSSGroup 分组。
    3. 如果该订阅源尚未关联任何分组，则创建新的 RSSFeedGroupLink 关联。

    Args:
        session (Session): 数据库会话。

    Returns:
        int: 成功迁移的订阅源数量。
    """
    # 查找所有有 group_name 的 feed
    feeds = session.exec(select(RSSFeed).where(RSSFeed.group_name != None)).all()

    count = 0
    for feed in feeds:
        if not feed.group_name:
            continue

        group_name = feed.group_name.strip()
        if not group_name:
            continue

        # 查找或创建对应名称的分组
        group = session.exec(select(RSSGroup).where(RSSGroup.name == group_name)).first()
        if not group:
            group = RSSGroup(name=group_name)
            session.add(group)
            session.commit()
            session.refresh(group)

        # 检查订阅源是否已关联了分组
        if not feed.groups: # 如果还没有任何分组关联
             link = RSSFeedGroupLink(feed_id=feed.id, group_id=group.id)
             session.add(link)
             count += 1

        # 注意：此处保留了旧字段的数据，暂未清空 feed.group_name 作为备份

    if count > 0:
        session.commit()
        logger.info(f"Migrated {count} feeds from legacy group_name")

    return count

def fetch_feed_background(feed_url: str, feed_id: int = None):
    """
    后台任务包装器：抓取单个订阅源。

    Args:
        feed_url (str): 订阅源 URL。
        feed_id (int, optional): 订阅源 ID。
    """
    with Session(engine) as session:
        fetch_and_parse_feed(feed_url, session, feed_id)

def update_all_feeds_background():
    """
    后台任务：刷新所有处于启用状态的订阅源。
    """
    with Session(engine) as session:
        # 只更新启用的 Feed
        feeds = session.exec(select(RSSFeed).where(RSSFeed.is_active == True)).all()
        logger.info(f"Starting background refresh for {len(feeds)} feeds...")
        count = 0
        for feed in feeds:
            try:
                fetch_and_parse_feed(feed.url, session, feed.id)
                count += 1
            except Exception as e:
                logger.error(f"Failed to refresh feed {feed.url}: {e}")
        logger.info(f"Background refresh completed. Updated {count} feeds.")

def auto_classify_feeds(session: Session):
    """
    Auto classify feeds into groups using LLM.
    Also migrates legacy group_name data first.
    """
    migrated_count = 0
    # 0. Migrate legacy data first
    try:
        migrated_count = migrate_legacy_groups(session)
        if migrated_count > 0:
            logger.info(f"Auto-migration: Migrated {migrated_count} feeds from legacy group_name")
    except Exception as e:
        logger.error(f"Auto-migration failed: {e}")

    # 1. Get unclassified feeds
    # Find feeds that have NO entries in RSSFeedGroupLink OR only linked to 'Top RSS List'

    # Get ID of 'Top RSS List'
    top_group = session.exec(select(RSSGroup).where(RSSGroup.name == "Top RSS List")).first()
    top_group_id = top_group.id if top_group else None

    # Query feeds with groups preloaded
    statement = select(RSSFeed).where(RSSFeed.is_active == True).options(selectinload(RSSFeed.groups))
    all_feeds = session.exec(statement).all()

    feeds = []
    for feed in all_feeds:
        if not feed.groups:
            feeds.append(feed)
        elif len(feed.groups) == 1 and top_group_id and feed.groups[0].id == top_group_id:
             feeds.append(feed)

    if not feeds:
        return {"message": "No unclassified feeds found", "count": 0}

    logger.info(f"Found {len(feeds)} unclassified feeds to process")

    # 2. Get existing groups
    groups = session.exec(select(RSSGroup)).all()
    group_names = [g.name for g in groups]

    # 3. Batch process
    batch_size = 10
    total_processed = 0

    chat_service = ChatService()
    # Get a model. Prefer OpenAI or high capability model.
    models = chat_service.get_enabled_models()
    if not models:
        # If no models enabled, return error
        logger.error("No enabled AI models found for auto-classify")
        raise ValueError("No AI models enabled")
    model_id = models[0]["id"] # Use first enabled

    provider, config = chat_service.get_provider_for_model(model_id)
    if not provider:
         logger.error(f"Provider not found for model {model_id}")
         raise ValueError(f"Provider not found for model {model_id}")

    logger.info(f"Using AI model {model_id} for auto-classification")

    for i in range(0, len(feeds), batch_size):
        batch = feeds[i:i+batch_size]
        feed_info = "\n".join([f"- ID:{f.id} Title:{f.title} Desc:{f.description[:100] if f.description else ''}" for f in batch])

        prompt = f"""
You are an intelligent RSS feed organizer.
I have the following RSS feeds:
{feed_info}

And the following existing groups:
{', '.join(group_names)}

Please classify each feed into ONE of the existing groups.
If a feed clearly does not fit any existing group, suggest a concise, standard new group name (e.g., "Technology", "News", "Blog", "Programming").
Return ONLY a valid JSON array of objects, where each object has "id" (integer) and "group" (string).
Example: [{{"id": 1, "group": "Tech"}}, {{"id": 2, "group": "News"}}]
Do not include any other text or markdown formatting.
"""
        messages = [{"role": "user", "content": prompt}]

        try:
            # We use generate_stream but consume it all
            response_stream = provider.generate_stream(messages, config)
            full_response = "".join([chunk for chunk in response_stream])

            logger.info(f"AI Response: {full_response[:200]}...") # Log partial response for debug

            # Clean response
            cleaned_response = full_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            cleaned_response = cleaned_response.strip()

            results = json.loads(cleaned_response)

            for res in results:
                feed_id = res.get("id")
                group_name = res.get("group")

                if not feed_id or not group_name:
                    continue

                # Check if group exists
                group = next((g for g in groups if g.name == group_name), None)
                if not group:
                    # Create new group
                    # Check DB again to avoid duplicates in parallel batches (though we run sequentially here)
                    group = session.exec(select(RSSGroup).where(RSSGroup.name == group_name)).first()
                    if not group:
                        group = RSSGroup(name=group_name)
                        session.add(group)
                        session.commit()
                        session.refresh(group)
                    if group not in groups:
                        groups.append(group) # Add to local cache

                # Link feed to group
                # Check if this specific link exists
                existing_link = session.exec(select(RSSFeedGroupLink).where(
                    RSSFeedGroupLink.feed_id == feed_id,
                    RSSFeedGroupLink.group_id == group.id
                )).first()

                if not existing_link:
                    link = RSSFeedGroupLink(feed_id=feed_id, group_id=group.id)
                    session.add(link)

                    # Remove from Top RSS List if applicable (re-classify)
                    if top_group_id and group.id != top_group_id:
                         top_link = session.exec(select(RSSFeedGroupLink).where(
                            RSSFeedGroupLink.feed_id == feed_id,
                            RSSFeedGroupLink.group_id == top_group_id
                        )).first()
                         if top_link:
                             session.delete(top_link)

            session.commit()
            total_processed += len(results)

        except Exception as e:
            logger.error(f"Error classifying batch: {e}")
            continue

    logger.info(f"Auto classification completed. Processed {total_processed + migrated_count} feeds.")
    return {"message": "Auto classification completed", "count": total_processed + migrated_count}
