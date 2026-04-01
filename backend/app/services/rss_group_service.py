from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, col, func
from app.models.rss import RSSGroup, RSSGroupCreate, RSSGroupUpdate, RSSFeed, RSSFeedGroupLink

class RSSGroupService:
    """
    处理 RSS 分组相关的业务逻辑服务类，提供分组的增删改查以及订阅源关联管理。
    """
    
    def create_group(self, session: Session, group_create: RSSGroupCreate) -> RSSGroup:
        """
        创建一个新的 RSS 分组。

        Args:
            session (Session): 数据库会话。
            group_create (RSSGroupCreate): 包含新分组数据的数据模型。

        Returns:
            RSSGroup: 创建成功的分组记录。
        """
        group = RSSGroup.from_orm(group_create)
        session.add(group)
        session.commit()
        session.refresh(group)
        return group

    def get_group(self, session: Session, group_id: int) -> Optional[RSSGroup]:
        """
        根据 ID 获取单个 RSS 分组。

        Args:
            session (Session): 数据库会话。
            group_id (int): 分组的唯一 ID。

        Returns:
            Optional[RSSGroup]: 找到的分组记录，如果不存在则返回 None。
        """
        return session.get(RSSGroup, group_id)

    def get_groups(self, session: Session, parent_id: Optional[int] = None) -> List[RSSGroup]:
        """
        获取指定父节点下的所有分组。如果不指定 parent_id，则获取所有顶层分组。
        结果按 order 字段升序排列。

        Args:
            session (Session): 数据库会话。
            parent_id (Optional[int], optional): 父分组 ID。默认为 None。

        Returns:
            List[RSSGroup]: 分组记录列表。
        """
        statement = select(RSSGroup)
        if parent_id is not None:
            statement = statement.where(RSSGroup.parent_id == parent_id)
        statement = statement.order_by(RSSGroup.order)
        return session.exec(statement).all()

    def get_all_groups(self, session: Session) -> List[RSSGroup]:
        """
        获取系统中的所有分组，按 order 字段升序排列。

        Args:
            session (Session): 数据库会话。

        Returns:
            List[RSSGroup]: 所有分组的列表。
        """
        return session.exec(select(RSSGroup).order_by(RSSGroup.order)).all()

    def get_groups_tree(self, session: Session) -> List[Dict[str, Any]]:
        """
        获取包含层级结构的分组树，并计算每个分组下的订阅源数量。

        Args:
            session (Session): 数据库会话。

        Returns:
            List[Dict[str, Any]]: 格式化的树形分组列表，顶层为根节点，子节点存放在 'children' 键中。
        """
        groups = self.get_all_groups(session)

        # 优化：批量查询每个分组关联的 feed 数量，避免 N+1 查询问题
        feed_counts = session.exec(
             select(RSSFeedGroupLink.group_id, func.count(RSSFeedGroupLink.feed_id))
             .group_by(RSSFeedGroupLink.group_id)
        ).all()
        count_map = {group_id: count for group_id, count in feed_counts}

        # 构建映射字典以避免模型/字典的转换问题
        group_map = {}
        for g in groups:
            group_map[g.id] = {
                "id": g.id,
                "name": g.name,
                "parent_id": g.parent_id,
                "icon": g.icon,
                "color": g.color,
                "order": g.order,
                "feeds_count": count_map.get(g.id, 0),
                "children": []
            }

        # 组装树形结构
        roots = []
        for g in groups:
            current_node = group_map[g.id]
            if g.parent_id and g.parent_id in group_map:
                group_map[g.parent_id]['children'].append(current_node)
            else:
                roots.append(current_node)

        return roots

    def update_group(self, session: Session, group_id: int, group_update: RSSGroupUpdate) -> Optional[RSSGroup]:
        """
        更新指定分组的信息。

        Args:
            session (Session): 数据库会话。
            group_id (int): 要更新的分组 ID。
            group_update (RSSGroupUpdate): 包含更新内容的数据模型。

        Returns:
            Optional[RSSGroup]: 更新后的分组记录，如果未找到则返回 None。
        """
        group = session.get(RSSGroup, group_id)
        if not group:
            return None
        group_data = group_update.dict(exclude_unset=True)
        for key, value in group_data.items():
            setattr(group, key, value)
        session.add(group)
        session.commit()
        session.refresh(group)
        return group

    def delete_group(self, session: Session, group_id: int) -> bool:
        """
        删除指定的分组。如果该分组有子分组，则将子分组的 parent_id 设为 None（移至根节点）。

        Args:
            session (Session): 数据库会话。
            group_id (int): 要删除的分组 ID。

        Returns:
            bool: 删除成功返回 True，如果未找到分组返回 False。
        """
        group = session.get(RSSGroup, group_id)
        if not group:
            return False

        # 检查是否有子分组
        children = session.exec(select(RSSGroup).where(RSSGroup.parent_id == group_id)).all()
        if children:
             # 如果有子分组，防止级联删除意外，将子分组的 parent_id 置空
             for child in children:
                 child.parent_id = None
                 session.add(child)

        session.delete(group)
        session.commit()
        return True

    def add_feed_to_group(self, session: Session, feed_id: int, group_id: int):
        """
        将指定的订阅源添加到一个分组中。

        Args:
            session (Session): 数据库会话。
            feed_id (int): 订阅源 ID。
            group_id (int): 分组 ID。
        """
        # 检查关联是否已存在
        existing = session.get(RSSFeedGroupLink, (feed_id, group_id))
        if not existing:
            link = RSSFeedGroupLink(feed_id=feed_id, group_id=group_id)
            session.add(link)
            session.commit()

    def remove_feed_from_group(self, session: Session, feed_id: int, group_id: int):
        """
        将指定的订阅源从分组中移除。

        Args:
            session (Session): 数据库会话。
            feed_id (int): 订阅源 ID。
            group_id (int): 分组 ID。
        """
        link = session.get(RSSFeedGroupLink, (feed_id, group_id))
        if link:
            session.delete(link)
            session.commit()

    def set_feed_groups(self, session: Session, feed_id: int, group_ids: List[int]):
        """
        重新设置订阅源所属的分组。这会清除之前所有的分组关联并建立新的关联。

        Args:
            session (Session): 数据库会话。
            feed_id (int): 订阅源 ID。
            group_ids (List[int]): 新的分组 ID 列表。
        """
        # 移除已有的所有关联记录
        links = session.exec(select(RSSFeedGroupLink).where(RSSFeedGroupLink.feed_id == feed_id)).all()
        for link in links:
            session.delete(link)

        # 添加新的关联记录
        for gid in group_ids:
            link = RSSFeedGroupLink(feed_id=feed_id, group_id=gid)
            session.add(link)
        session.commit()

rss_group_service = RSSGroupService()
