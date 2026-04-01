from sqlmodel import Session, select
from app.models.user_profile import UserProfile, UserProfileUpdate, UserProfileHistory
from datetime import datetime

class UserProfileService:
    """
    处理用户个人信息（UserProfile）业务逻辑的服务类。
    提供获取个人信息、更新个人信息及查询修改历史的功能。
    """

    def get_profile(self, session: Session) -> UserProfile:
        """
        获取当前用户的个人信息记录。
        如果数据库中不存在记录，则自动创建并返回一个默认的空记录。

        业务逻辑：
        - 当前系统假设为单用户环境，始终获取或创建 ID=1 的记录。

        Args:
            session (Session): 数据库会话。

        Returns:
            UserProfile: 用户的个人信息对象。
        """
        # 假设单用户系统，始终获取 ID=1 的记录
        statement = select(UserProfile).where(UserProfile.id == 1)
        profile = session.exec(statement).first()

        if not profile:
            # 初始化默认数据
            profile = UserProfile(id=1, identity="", rules="")
            session.add(profile)
            session.commit()
            session.refresh(profile)

        return profile

    def update_profile(self, session: Session, update_data: UserProfileUpdate) -> UserProfile:
        """
        更新用户的个人信息，并在更新前将旧数据存入历史记录表。

        业务逻辑：
        1. 获取当前的最新的个人信息记录。
        2. 将当前的 `identity` 和 `rules` 数据保存到 `UserProfileHistory` 表中。
        3. 根据传入的更新数据更新当前记录，并修改更新时间。

        Args:
            session (Session): 数据库会话。
            update_data (UserProfileUpdate): 包含要更新的身份或规则数据。

        Returns:
            UserProfile: 更新后的用户个人信息对象。
        """
        profile = self.get_profile(session)

        # 保存更新前的历史记录
        history = UserProfileHistory(
            profile_id=profile.id,
            identity=profile.identity,
            rules=profile.rules,
            created_at=datetime.utcnow()
        )
        session.add(history)

        # 增量更新提供的字段
        if update_data.identity is not None:
            profile.identity = update_data.identity
        if update_data.rules is not None:
            profile.rules = update_data.rules

        profile.updated_at = datetime.utcnow()
        session.add(profile)
        session.commit()
        session.refresh(profile)
        return profile

    def get_history(self, session: Session, limit: int = 10) -> list[UserProfileHistory]:
        """
        获取用户个人信息的修改历史列表。

        Args:
            session (Session): 数据库会话。
            limit (int, optional): 返回记录的最大数量，默认 10 条。

        Returns:
            list[UserProfileHistory]: 按创建时间倒序排列的历史记录列表。
        """
        statement = select(UserProfileHistory).order_by(UserProfileHistory.created_at.desc()).limit(limit)
        return session.exec(statement).all()

user_profile_service = UserProfileService()
