from sqlmodel import Session, select, func
from app.models.user_profile import UserProfile, UserProfileUpdate, UserProfileHistory
from app.models.user import User
from datetime import datetime
from typing import Optional

class UserProfileService:
    """
    处理用户个人信息（UserProfile）业务逻辑的服务类。
    提供获取个人信息、更新个人信息及查询修改历史的功能。
    支持多用户环境，每个用户拥有独立的配置和历史版本管理。
    """

    def get_profile(self, session: Session, user_id: int) -> UserProfile:
        """
        获取指定用户的个人信息记录。
        如果数据库中不存在记录，则自动创建并返回一个默认的空记录。

        业务逻辑：
        - 根据 user_id 查询用户的个人信息配置
        - 如果不存在，则创建默认配置并关联到用户

        Args:
            session (Session): 数据库会话。
            user_id (int): 用户ID。

        Returns:
            UserProfile: 用户的个人信息对象。

        Raises:
            ValueError: 用户不存在时抛出异常。
        """
        # 验证用户是否存在
        user = session.get(User, user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")

        # 查询用户的个人信息配置
        statement = select(UserProfile).where(UserProfile.user_id == user_id)
        profile = session.exec(statement).first()

        if not profile:
            # 初始化默认数据，关联到用户
            profile = UserProfile(
                user_id=user_id,
                identity="",
                rules=""
            )
            session.add(profile)
            session.commit()
            session.refresh(profile)

        return profile

    def update_profile(
        self,
        session: Session,
        user_id: int,
        update_data: UserProfileUpdate,
        change_reason: Optional[str] = None
    ) -> UserProfile:
        """
        更新用户的个人信息，并在更新前将旧数据存入历史记录表。

        业务逻辑：
        1. 获取当前的最新的个人信息记录。
        2. 查询当前最大版本号，新版本号 = 最大版本号 + 1。
        3. 将当前的 `identity` 和 `rules` 数据保存到 `UserProfileHistory` 表中。
        4. 根据传入的更新数据更新当前记录，并修改更新时间。

        Args:
            session (Session): 数据库会话。
            user_id (int): 用户ID。
            update_data (UserProfileUpdate): 包含要更新的身份或规则数据。
            change_reason (Optional[str]): 变更原因说明，可选。

        Returns:
            UserProfile: 更新后的用户个人信息对象。
        """
        # ========== 步骤1：获取当前配置 ==========
        profile = self.get_profile(session, user_id)

        # ========== 步骤2：获取当前最大版本号 ==========
        max_version_statement = (
            select(func.max(UserProfileHistory.version))
            .where(UserProfileHistory.user_id == user_id)
        )
        max_version = session.exec(max_version_statement).first() or 0
        new_version = max_version + 1

        # ========== 步骤3：保存更新前的历史记录 ==========
        history = UserProfileHistory(
            user_id=user_id,
            identity=profile.identity,
            rules=profile.rules,
            version=new_version,
            change_reason=change_reason,
            created_at=datetime.utcnow()
        )
        session.add(history)

        # ========== 步骤4：增量更新提供的字段 ==========
        if update_data.identity is not None:
            profile.identity = update_data.identity
        if update_data.rules is not None:
            profile.rules = update_data.rules

        profile.updated_at = datetime.utcnow()
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile

    def get_history(self, session: Session, user_id: int, limit: int = 10) -> list[UserProfileHistory]:
        """
        获取指定用户个人信息的修改历史列表。

        Args:
            session (Session): 数据库会话。
            user_id (int): 用户ID。
            limit (int, optional): 返回记录的最大数量，默认 10 条。

        Returns:
            list[UserProfileHistory]: 按版本号倒序排列的历史记录列表。
        """
        statement = (
            select(UserProfileHistory)
            .where(UserProfileHistory.user_id == user_id)
            .order_by(UserProfileHistory.version.desc())
            .limit(limit)
        )
        return session.exec(statement).all()

    def rollback_to_version(
        self,
        session: Session,
        user_id: int,
        target_version: int,
        change_reason: Optional[str] = None
    ) -> UserProfile:
        """
        回溯到指定版本。

        业务逻辑：
        1. 查询目标版本的历史记录。
        2. 保存当前状态为新版本（回溯前备份）。
        3. 应用历史版本的配置。

        Args:
            session (Session): 数据库会话。
            user_id (int): 用户ID。
            target_version (int): 目标版本号。
            change_reason (Optional[str]): 变更原因说明，可选。

        Returns:
            UserProfile: 回溯后的用户个人信息对象。

        Raises:
            ValueError: 目标版本不存在时抛出异常。
        """
        # ========== 步骤1：查询目标版本的历史记录 ==========
        history_statement = (
            select(UserProfileHistory)
            .where(UserProfileHistory.user_id == user_id)
            .where(UserProfileHistory.version == target_version)
        )
        target_history = session.exec(history_statement).first()

        if not target_history:
            raise ValueError(f"Version {target_version} not found for user {user_id}")

        # ========== 步骤2：获取当前配置 ==========
        current_profile = self.get_profile(session, user_id)

        # ========== 步骤3：保存当前状态为新版本（回溯前备份） ==========
        max_version_statement = (
            select(func.max(UserProfileHistory.version))
            .where(UserProfileHistory.user_id == user_id)
        )
        max_version = session.exec(max_version_statement).first() or 0
        backup_version = max_version + 1

        backup_history = UserProfileHistory(
            user_id=user_id,
            identity=current_profile.identity,
            rules=current_profile.rules,
            version=backup_version,
            change_reason=change_reason or f"回溯前备份（目标版本：{target_version}）",
            created_at=datetime.utcnow()
        )
        session.add(backup_history)

        # ========== 步骤4：应用历史版本 ==========
        current_profile.identity = target_history.identity
        current_profile.rules = target_history.rules
        current_profile.updated_at = datetime.utcnow()

        session.add(current_profile)
        session.commit()
        session.refresh(current_profile)

        return current_profile

user_profile_service = UserProfileService()
